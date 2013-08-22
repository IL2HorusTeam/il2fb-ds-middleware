# -*- coding: utf-8 -*-


class LineReceiverTestCaseMixin:

    def _get_unexpecting_line_receiver(self, d):

        def got_line(line, peer):
            timeout.cancel()
            d.errback(FailTest("Unexpected data from {0}:\n\t{1}.".format(
                peer, line)))

        from twisted.internet import reactor
        timeout = reactor.callLater(0.1, d.callback, None)
        return got_line

    def _get_expecting_line_receiver(self, expected_responses, d):

        def got_line(line):
            try:
                self.assertEqual(line, expected_responses.pop(0))
            except Exception as e:
                timeout.cancel()
                d.errback(e)
            else:
                if expected_responses:
                    return
                timeout.cancel()
                d.callback(None)

        def on_timeout(_):
            d.errback(FailTest(
            'Timed out, remaining lines:\n\t'+'\n\t'.join(expected_responses)))

        from twisted.internet import reactor
        timeout = reactor.callLater(0.1, on_timeout, None)
        return got_line
