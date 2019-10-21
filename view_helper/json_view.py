import json
import math
from copy import deepcopy
from datetime import datetime, timedelta, date
from json import JSONEncoder

import arrow
from django.db.models import QuerySet, Model
from django.forms import model_to_dict
from django.http import JsonResponse
from django.views.generic.base import View

from .errors import InvalidParams
from .time import TIME_FORMAT, DATE_FORMAT
from .utils import delete_keys


class Paginator:
    paginate_names = [('page', 1), ('limit', 10), ('sort', None), ('order', 'desc')]
    pagination_switch_key = 'pagination'

    def __init__(self, obj):
        """
        :param obj: object hast properties page, limit, sort, order
        """
        self.obj = obj

    def get_paging_arguments(self):
        def _get(name, default):
            v = getattr(self.obj, name, None)
            if not v:
                return default
            if name in ['page', 'limit']:
                v = int(v)
            return v

        return {
            name_default[0]: _get(*name_default) for name_default in self.paginate_names
        }

    @staticmethod
    def remove_paginator_keys(data):
        data = deepcopy(data)
        delete_keys(
            data,
            [x[0] for x in Paginator.paginate_names]
            + [Paginator.pagination_switch_key],
        )
        return data

    def parse(self, qs):
        pagination = getattr(
            self.obj, self.pagination_switch_key, None
        )  # True, False, None
        paging = self.get_paging_arguments()
        qs, paginate_meta = self.paginate_queryset(qs, pagination, **paging)
        return qs, paginate_meta

    @staticmethod
    def paginate_queryset(qs, pagination: bool, page, limit, sort, order):
        if sort:
            order_by_arg = ("-" if order == "desc" else "") + sort
            qs = qs.order_by(order_by_arg)

        count = qs.count()
        offset = limit * (page - 1)

        # if offset > count or page <= 0:
        #     raise InvalidParams("index or max argument overflow")

        if pagination is False:
            meta = {
                "count": count,
                "limit": count,
                "page": 1,
                "pages": 1,
                # 'sort': sort,
                # 'order': order,
            }
            return qs, meta
        else:
            pages = int(math.ceil(count / limit))
            qs = qs[offset : offset + limit]
            meta = {
                "count": count,
                "limit": limit,
                "page": page,
                "pages": pages or 1,
                # 'sort': sort,
                # 'order': order,
            }
            return qs, meta


class CustomJSONEncoder(JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time, enum, django model and other things
    """

    def default(self, o):
        # See "Date Time String Format" in the ECMA-262 specification.
        # the order of datetime, date matter due to datetime being subclass of date
        if isinstance(o, datetime):
            # Assume this object has `tzinfo` or is a UTC time
            return arrow.get(o).format(TIME_FORMAT)
        if isinstance(o, date):
            return o.strftime(DATE_FORMAT)
        if isinstance(o, QuerySet):
            return list(o)
        if isinstance(o, Model):
            return model_to_dict(o)
        else:
            return super().default(o)


class JSONView(View):
    @property
    def json(self):
        if self.request.method != "POST":
            raise Exception("should be called on post request")

        if not hasattr(self, "_json"):
            try:
                self._json = json.loads(self.request.body)
            except Exception as e:
                raise InvalidParams("could not parse body as json: {}".format(e))
        return self._json

    @staticmethod
    def json_response(data, status=200, encoder=None, as_root_data=False):
        encoder = encoder or CustomJSONEncoder
        if as_root_data:
            data = {"data": data}
        return JsonResponse(
            data,
            json_dumps_params={'ensure_ascii': False},
            encoder=encoder,
            status=status,
            safe=False,
        )

    def error_response(self, error, status, code, errors=None):
        d = {"code": code, "message": error}
        if errors:
            d['errors'] = errors
        return self.json_response(d, status)

    def logged_in(self, req):
        return not (req.user and req.user.is_anonymous)

    def make_paging_response(
        self, req, qs, encoder=None, post_item=None, post_data=None
    ):
        _paginator = Paginator(req.params)
        qs, paginate_meta = _paginator.parse(qs)
        rv = {'data': qs, 'pagination': paginate_meta}
        if post_item:
            rv['data'] = [post_item(x) for x in rv['data']]
        if encoder:
            # convert to dict
            rv['data'] = json.loads(json.dumps(qs, cls=encoder))
        if post_data:
            if not encoder:
                raise Exception('missing encoder to apply post_data')
            # update dict
            rv['data'] = post_data(rv['data'])
        return self.json_response(rv)

    def process_start_end_date(self, data, field_names=("updated_at", "created_at")):
        data = Paginator.remove_paginator_keys(data)
        for name in field_names:
            start = data.pop(f"{name}_start", None)
            end = data.pop(f"{name}_end", None)
            if start:
                # start = make_aware_utc(start)
                assert isinstance(start, datetime)
                assert start.tzinfo, f'got tzinfo {start.tzinfo}'
                data["{}__gte".format(name)] = start
            if end:
                # end = make_aware_utc(end)
                assert isinstance(end, datetime)
                assert end.tzinfo, f'got tzinfo {end.tzinfo}'
                data["{}__lt".format(name)] = end + timedelta(days=1)
        return data
