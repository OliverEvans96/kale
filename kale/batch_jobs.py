# stdlib
import time
import os
import sys
import subprocess
import random
import xml.etree.ElementTree as et
import logging

# 3rd party
import tempfile

def determine_batch_manager():
    options = {
        'torque': 'qsub',
        'slurm': 'sbatch'
    }

    for manager, command in options.items():
        # Returns 0 if option exists, 1 otherwise
        if not subprocess.call(['which', command]):
            return manager

    raise ValueError("Could not locate batch manager.")

def wait_for_fifo(path, key):
    "Wait for key to be written to path. Pass if correct, fail otherwise."
    with open(path) as fh:
        if fh.read() == key:
            pass
        else:
            sys.exit(1)

def gen_fifo():
    fname = subprocess.getoutput('mktemp -u -p . -t .watch_nb.XXXXXXXXXX').strip()
    subprocess.call(['mkfifo',fname])
    return fname

def gen_random_hash():
    return "%032x" % random.getrandbits(128)

def job_running_or_queued(job_id, batch_manager):
    if batch_manager == 'torque':
        return torque_job_running_or_queued(job_id)
    else:
        raise NotImplementedError(
            "Batch manager {} not supported".format(
                batch_manager
            )
        )

def torque_job_running_or_queued(job_id):
    """Determine if torque job is running by id

    Parameters
    ----------
    job_id : int        Job number, without batch queue

    Returns
    -------
    running : bool      Whether the job is currently running
    """

    qstat_xml = subprocess.check_output(
        'qstat -x',
        shell=True
    ).decode().strip()

    xml_data = et.fromstring(qstat_xml)

    logging.info("Torque - Looking for job {}".format(job_id))

    for job in xml_data:
        # Convert xml to dict

        this_job_id = job.findtext('Job_Id')

        #logging.debug("Checking job {}".format(this_job_id))
        #job_dict = {prop.tag: prop.text for prop in job}
        #logging.debug(job_dict)

        # If this is the correct job
        if this_job_id == job_id:
            logging.info("Found matching job.")
            job_state = job.findtext('job_state')

            # If the job is running
            if job_state in 'RQ':
                logging.info("Job is running or queued (%s).", job_state)
                return True

            # If the desired job is not running:
            else:
                logging.info(
                    "Job not running - state is '{}'".format(
                        job_state
                    )
                )
                return False
        #else:
            #logging.debug("Not a match.")

    # If the job is not found, raise an exception
    logging.warning("Job {} not found.".format(job_id))
    return False
    #raise NameError('Job {} not found'.format(job_id))


def get_tempfile():
    return subprocess.check_output('mktemp').decode().strip()

def create_appended_text_file(path, addition):
    fname = os.path.basename(path)
    newpath = get_tempfile()

    with open(path) as fh:
        content = fh.read()

    with open(newpath, 'w') as fh:
        fh.write(content)
        fh.write('\n')
        fh.write(addition)

    return newpath

def create_success_file():
    fd, path = tempfile.mkstemp(prefix='.watch_job_', dir='.')
    os.close(fd)
    return path

def wrap_batch_script(batch_script, success_file, randhash):
    success_command = """

    cat {success_file} > tmp_success_file.{randhash}
    stdbuf -o0 -e0 echo '{randhash}' > {success_file}
    while [ -z $(grep -Fx '{randhash}' '{success_file}') ]
    do
        sleep 1
    done
    cat {success_file} >> tmp_success_file.{randhash}
    """.format(
        randhash=randhash,
        success_file=success_file
    )

    new_batch_script = create_appended_text_file(
        batch_script,
        success_command
    )

    return new_batch_script

def submit_batch_script(script_path):
    """Submit job, decode job_id bytes & remove newline
    Holds are passed to qsub via -h.
    """
    #with open(script_path) as fh:
    #    print(fh.read())

    batch_manager = determine_batch_manager()
    if batch_manager == 'torque':
        sub_cmd = 'qsub'
    elif batch_manager == 'slurm':
        sub_cmd = 'sbatch --parsable'

    command = ' '.join([sub_cmd, script_path])
    logging.debug("QSUB COMMAND: {}".format(command))
    return subprocess.check_output(command, shell=True).decode().strip()

def poll_success_file(filepath, job_id, randhash, poll_interval):
    batch_manager = determine_batch_manager()

    try:
        #print("Before while")
        while job_running_or_queued(job_id, batch_manager):
            logging.debug('Job running or queued. Sleeping for %s seconds.', poll_interval)
            time.sleep(poll_interval)

        logging.info('Job not running or queued. Sleeping for 3 seconds.')
        time.sleep(3)
        # Job is no longer in batch queue
        try:
            logging.info("Checking file '%s' for hash", filepath)
            with open(filepath) as fh:
                message = fh.read().strip()
                logging.debug("Message is '%s'", message)
            if message == randhash:
                logging.info("Hash correct. Job success.")
            elif message == '':
                logging.error("Empty message. Job failed.")
                #sys.exit(1)
            else:
                logging.error("Wrong hash!")
                logging.error("Wanted '{}'".format(randhash))
                logging.error("Received '{}'".format(message))
                #sys.exit(1)
        except FileNotFoundError:
            # No success message means job failed
            logging.error("Unexpected error. File not found.")
            #sys.exit(1)
    finally:
        # Always delete success file
        os.remove(filepath)
        logging.debug("Deleted hash file %s", filepath)

def run_batch_job(batch_script, node_property=None, poll_interval=60):
    """Run batch job.

    Parameters
    ----------
    batch_script : str          Path of batch script
    node_property : str         Run only on node with this property
    poll_interval : int         Number of seconds between completion checks
    """
    logging.info("""Run batch job.
    batch_script = '%s'
    node_property = '%s'
    poll_interval = '%s'
    """, batch_script, node_property, poll_interval)
    success_file = create_success_file()
    randhash = gen_random_hash()

    new_batch_script = wrap_batch_script(
        batch_script,
        success_file,
        randhash
    )

    job_id = submit_batch_script(new_batch_script)

    logging.info("Job submitted. Polling success file.")
    poll_success_file(success_file, job_id, randhash, poll_interval)
    logging.info("Polling complete. run_batch_job finished.")

def get_nodes_string(nodes_cores, node_property):
    """
    nodes_cores is a dict with nodes as keys, num_cores as items.
    Alternatively, it can be an int with # of cores.
    """

    batch_manager = determine_batch_manager()
    if batch_manager == 'torque':
        if type(nodes_cores) is dict:
            node_string = '+'.join([
                '{node}:ppn={cores}'.format(node=node,cores=cores)
                for node,cores in nodes_cores.items()
            ])
        elif type(nodes_cores) in (int, str):
            node_string = '1:ppn={}'.format(nodes_cores)
        else:
            raise ValueError("Received unexpected type for nodes_cores in get_nodes_string.")
        if node_property is not None:
            node_string += ':{}'.format(node_property)

    # DEFINITELY COULD BE IMPROVED
    elif batch_manager == 'slurm':
        if type(nodes_cores) is dict:
            node_string = str(len(nodes_cores.keys()))
        elif type(nodes_cores) in (int, str):
            node_string = '1'

    return node_string


def create_dir_for_file(filepath):
    """Create the directory containing `filepath` if it doesn't exist"""
    os.makedirs(
        os.path.dirname(filepath),
        exist_ok=True
    )


# TODO - review
def run_cmd_job(command, name, nodes_cores, log_dir='.', time='10:00', node_property=None, poll_interval=60, mpiexec="/opt/open-mpi/ib-gnu44/bin/mpiexec"):
    tmp_batch_script = get_tempfile()
    batch_manager = determine_batch_manager()
    if batch_manager == 'torque':
        batch_template = """#!/bin/bash
#PBS -l nodes={nodes_string}
#PBS -l nice=10
#PBS -j oe
#PBS -q default
#PBS -N {name}
#PBS -o {log_dir}/{name}.log
#PBS -r n
cd $PBS_O_WORKDIR
{command}"""
    elif batch_manager == 'slurm':
        batch_template = """#!/bin/bash
#SBATCH -J {name}
#SBATCH -p debug
#SBATCH -N {nodes_string}
#SBATCH -t {time}
#SBATCH -o {log_dir}/{name}.log
#SBATCH -C haswell
#SBATCH -L SCRATCH
{command}"""

    batch_string = batch_template.format(
        #{mpiexec} {command}""".format(
        command=command,
        name=name,
        time=time,
        log_dir=log_dir,
        #mpiexec=mpiexec,
        nodes_string=get_nodes_string(nodes_cores, node_property)
    )

    #print("Run cmd job.")
    #print(batch_string)

    with open(tmp_batch_script, 'w') as fh:
        fh.write(batch_string)

    # Make sure log directory exists
    logpath = "{log_dir}/{name}".format(
        log_dir=log_dir,
        name=name
    )
    create_dir_for_file(logpath)
    logging.debug("Created logpath for {}".format(logpath))

    run_batch_job(tmp_batch_script, poll_interval)
