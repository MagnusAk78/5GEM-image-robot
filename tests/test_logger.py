# -*- coding: utf-8 -*-

import helpers.logger

import unittest
from testfixtures import log_capture


class LoggerTestSuite(unittest.TestCase):
    """Logger test cases."""

    @log_capture()
    def test_log_info(self, l):
        logger = helpers.logger.setup_normal_logger('logger_name')
        logger.info('a message')
        logger.error('an error')
        l.check(
            ('logger_name', 'INFO', 'a message'),
            ('logger_name', 'ERROR', 'an error'),
        )


if __name__ == '__main__':
    unittest.main()