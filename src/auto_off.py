#!/usr/bin/env python
'''
#
# cr.imson.co
#
# Automated daily shutdown service for EC2 instances
#
# @author Damian Bushong <katana@odios.us>
#
'''

# pylint: disable=C0116,C0301,C0411,W0511,W1202

from crimsoncore import LambdaCore

from aws_xray_sdk.core import patch_all
patch_all()

LAMBDA_NAME = 'auto_off'
LAMBDA = LambdaCore(LAMBDA_NAME)
LAMBDA.init_ec2()
LAMBDA.init_s3()
LAMBDA.init_sns()

class RecoveredError(Exception): # pylint: disable=C0115
    pass

def lambda_handler(event, context):
    try:
        # pylint apparently doesn't understand that LAMBDA.ec2 is lazy-loaded.  disabling the rule for that line.
        instances = list(LAMBDA.ec2.instances.filter(Filters=[ # pylint: disable=E1101
            {
                'Name': 'tag:auto_off',
                'Values': ['True', 'true']
            },
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ]))

        if len(instances) > 0:
            had_failures = False
            for instance in instances:
                LAMBDA.logger.info(f'Stopping instance {instance.id}')

                try:
                    instance.stop()
                except Exception: # pylint: disable=W0703
                    LAMBDA.logger.error(f'Failed to stop instance {instance.id}', exc_info=True)
                    had_failures = True

            if had_failures:
                raise RecoveredError('One or more instance control failures occurred')
        else:
            LAMBDA.logger.info('No instances to stop.')
    except Exception:
        LAMBDA.logger.error('Fatal error during script runtime', exc_info=True)
        LAMBDA.send_notification('error', f'{LAMBDA_NAME} lambda error notification; reference logstream {LAMBDA.config.get_log_stream()}')

        raise
