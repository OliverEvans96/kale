import requests
from . import serialize

def remote_submit(wf, host='localhost', port=12643, endpoint='submit_parsl'):
    wf_bytes = serialize.serialize_wf(wf)
    return requests.post(
        "http://{host}:{port}/{endpoint}".format(
            host=host,
            port=port,
            endpoint=endpoint
        ),
        data=wf_bytes,
    )
