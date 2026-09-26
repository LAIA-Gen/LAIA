from datetime import datetime, timezone


async def run(context):
    user_id = context['element']['id']
    request = context['request_context']
    await context['repository'].post_item('loginevent', {
        'userId': user_id, 'createdAt': datetime.now(timezone.utc),
        'ipAddress': request['ip'], 'userAgent': request['user_agent'],
    })
