# Kale Manager Service

#stdlib
import sqlite3

# 3rd party
from flask import Flask, request
import dill

# kale
from . import workflow_objects
from . import serialize
from . import db

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

    # Retrieve request data
    wf_bytes = request.data

    # Connect to DB
    c = db.connect()
    db.init(c)

    # Store in DB
    # TODO: This should perhaps happen upon
    # execution rather than on submission?

    # Or, at least execution hooks must be
    # present to update task/WF status.
    wf_dict = dill.loads(wf_bytes)
    db.add_wf(c, wf_dict)

    # Create WorkerPool
    pool = workflow_objects.WorkerPool(
        wf_executor='parsl',
        num_workers=2,
        name='parsl_pool'
    )

    # Execute workflow
    wf = serialize.deserialize_wf(wf_bytes)
    pool.parsl_run(wf)

    return "TODO: supply num_workers via POST"

def main():
    print("Kale Manager Service Started.")
    app.run(port=listen_port, debug=True)

if __name__ == '__main__':
    main()
