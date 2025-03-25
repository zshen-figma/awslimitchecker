"""
awslimitchecker/metrics/statsd.py
"""

import os
import logging
import re
from awslimitchecker.metrics.base import MetricsProvider
from datadog import initialize, statsd

logger = logging.getLogger(__name__)

from datadog import initialize, statsd


class StatsD(MetricsProvider):
    """Send metrics to StatsD."""

    def __init__(
        self, region_name, prefix='awslimitchecker.',
        extra_tags=None, host='127.0.0.1', port=8125,
    ):
        """
        Initialize the StatsD metrics provider. This class does not have any
        additional requirements. 

        :param region_name: the name of the region we're connected to. This
          parameter is automatically passed in by the Runner class.
        :type region_name: str
        :param prefix: StatsD metric prefix
        :type prefix: str
        :param host: The StatsD host to use; defaults to
          ``127.0.0.1``. This parameter is overridden by the
          ``STATSD_HOST`` environment variable, if set. This must NOT end with
          a trailing slash.
        :type host: str
        :param port: The StatsD port to use; defaults to
          ``8125``. This parameter is overridden by the
          ``STATSD_PORT`` environment variable, if set. 
        :type port: str
        :param extra_tags: CSV list of additional tags to send with metrics.
          All metrics will automatically be tagged with ``region:<region name>``
        :type extra_tags: str
        """
        super(StatsD, self).__init__(region_name)
        self._prefix = prefix
        self._tags = ['region:%s' % region_name]
        if extra_tags is not None:
            self._tags.extend(extra_tags.split(','))
        self._host = os.environ.get('STATSD_HOST', host)
        self._port = os.environ.get('STATSD_PORT', port)

        options = {
            'statsd_host':self._host,
            'statsd_port':self._port
        }
        initialize(**options)

    def _name_for_metric(self, service, limit):
        """
        Return a metric name that's safe for datadog

        :param service: service name
        :type service: str
        :param limit: limit name
        :type limit: str
        :return: datadog metric name
        :rtype: str
        """
        return ('%s%s.%s' % (
            self._prefix,
            re.sub(r'[^0-9a-zA-Z]+', '_', service),
            re.sub(r'[^0-9a-zA-Z]+', '_', limit)
        )).lower()

    def flush(self):
        logger.debug('Flushing metrics to StatsD.')
        statsd.gauge('%sruntime' % self._prefix, self._duration, tags=self._tags)
        for lim in self._limits:
            u = lim.get_current_usage()
            if len(u) == 0:
                max_usage = 0
            else:
                max_usage = max(u).get_value()
            mname = self._name_for_metric(lim.service.service_name, lim.name)
            statsd.gauge('%s.max_usage' % mname, max_usage, tags=self._tags)
            limit = lim.get_limit()
            if limit is not None:
                statsd.gauge('%s.limit' % mname, limit, tags=self._tags)
