import kale.workflow_objects
import os.path

base_dir = '/home/oge1/kale/kale/examples'

t = kale.workflow_objects.Task('test')

lammps_wf = kale.workflow_objects.Workflow('lammps_wf')
lammps_wf.readme = """
<h1>LAMMPS Workflow</h1>
<br>
Simulate molecules from lattice moving from order to disorder
<br>
"""

lammps_task = kale.workflow_objects.BatchTask(
    name='lammps_task',
    batch_script=os.path.join(base_dir, "lammps_melt/melt_torque.batch"),
    notebook=os.path.join(base_dir,'LAMMPS Monitor.ipynb'),
    tags=['lammps'],
)
lammps_task.readme = """
Run modified LAMMPS melt example
"""
lammps_wf.add_task(lammps_task)

nb_task = kale.workflow_objects.NotebookTask(
    name='analysis_nb',
    notebook=os.path.join(base_dir,'notebooks/Analysis Notebook.ipynb'),
    tags=['analysis']
)
nb_task.readme = """
Post-simulation analysis notebook
"""
lammps_wf.add_task(nb_task, dependencies=[lammps_task])

