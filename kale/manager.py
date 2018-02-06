# Kale Manager Service

from flask import Flask, request
import kale
import kale.serialize as ser
import sqlite3

listen_port = 12643
app = Flask('kale')

# TODO
# Maintain sqlite3 DB of task/wf info added upon submission.
# Allow for querying this database for current status.

# Status of futures, etc. should be maintined in DB as well.
# This should be queryable via http request to get current status.

# Tasks should report back upon completion to update status
# (or be checked on periodically)

@app.route('/submit_parsl', methods=['POST'])
def submit_parsl():

    wf_bytes = request.data
    wf = ser.deserialize_wf(wf_bytes)
    pool = kale.workflow_objects.WorkerPool(
        wf_executor='parsl',
        num_workers=2,
        name='parsl_pool'
    )
    pool.parsl_run(wf)

def main():
    app.run(port=listen_port, debug=True)

if __name__ == '__main__':
    main()
