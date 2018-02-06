from . import workflow_objects
import dill

# Serialize DAG
def get_node_indices(nodes, wf):
    return [task.index[wf] for task in nodes]
def get_edge_indices(edges, wf):
    return [
        (t1.index[wf], t2.index[wf])
        for t1, t2 in edges
    ]
def sanitize_dag(wf):
    nodes = get_node_indices(wf.tasks)
    edges = get_edge_indices(wf.edges)
    return nodes, edges


# Deserialize DAG
def construct_dag(nodes, edges):
    dag = nx.DiGraph()
    dag.add_nodes_from(nodes)
    dag.add_edges_from(edges)
    return dag
def reconstruct_nodes(node_indices, index_dict):
    return [index_dict[index] for index in node_indices]
def reconstruct_edges(edge_indices, index_dict):
    return [
        (index_dict[index1],index_dict[index2])
         for index1, index2 in edge_indices
    ]


# Get state
def get_attr_list(obj, attrs):
    """Return dictionary with specified attributes from object if available.

    Parameters
    ----------
    obj : object
    attrs : list(str)

    Returns
    -------
    attr_dict : dict
    """
    all_attrs = dir(obj)
    return {attr: getattr(obj, attr) for attr in attrs if attr in all_attrs}

def get_task_state(task):
    """Get the relevant Task state."""
    attrs = [
        # Task
        'input_files',
        'output_files',
        'name',
        'readme',
        'log_path',
        'params',
        'tags',
        'task_type',
        'num_cores',
        'notebook',
        # PythonFunctionTask
        'func',
        'args',
        'kwargs',
        # CommandLineTask
        'command',
        'nodes_cores',
        'batch',
        # BatchTask
        'batch_script',
        'node_property',
        'poll_interval',
        # NotebookTask
        'interactive',
        'randhash',
        'success_file'
    ]
    state = get_attr_list(task, attrs)
    return state

def get_wf_state(wf):
    attrs = [
        'name',
        'readme',
        'index_dict',
        'dag'
    ]
    state = get_attr_list(wf, attrs)
    return state

# Sanitize

def sanitize_tasks(index_dict):
    return {
        index: get_task_state(task)
        for index, task in index_dict.items()
    }

# Reconstruct

def construct_task(task_state):
    """Construct Kale Task from state dict"""
    task_type = task_state.pop('task_type')
    if task_type == 'PythonFunctionTask':
        task = workflow_objects.PythonFunctionTask(**task_state)

    return task

def reconstruct_index_dict(index_dict_sanitized):
    return {
        index: construct_task(task_state)
        for index, task_state in index_dict_sanitized.items()
    }

def construct_wf(nodes, edges, **kwargs):
    wf = workflow_objects.Workflow(**kwargs)
    for node in nodes:
        wf.add_task(node)
    for edge in edges:
        wf.add_dependencies(task=edge[1], dependencies=[edge[0]])

    return wf

# Tests
def test_reconstruct_dag(wf):
    nodes = wf.dag.nodes()
    edges = wf.dag.edges()
    node_indices = get_node_indices(wf)
    edge_indices = get_edge_indices(wf)
    re_nodes = reconstruct_nodes(node_indices, wf)
    re_edges = reconstruct_edges(edge_indices, wf)

    assert (re_nodes == nodes) and (re_edges == edges)

def test_reconstruct_wf(wf):
    wf_bytes = serialize_wf(wf)
    re_wf = deserialize_wf(wf_bytes)

    assert serialize_wf(re_wf) == serialize_wf(wf)

## These are the useful functions

def serialize_wf(wf):
    """Serialize kale Workflow with dill.

    Captures all relevant information about tasks and their connections.
    Does not capture any futures or other transient state.
    Does serialize python function for PythonFunctionTasks.
    Ready to be sent over the wire via POST request.

    Parameters
    ----------
    wf : kale.workflow_objects.Workflow

    Returns
    -------
    wf_bytes : str (bytes)
    """

    state = get_wf_state(wf)

    # Sanitize tasks
    index_dict = state.pop('index_dict')
    state['index_dict_sanitized'] = sanitize_tasks(index_dict)

    # Sanitize DAG
    dag = state.pop('dag')
    node_indices = get_node_indices(wf.tasks, wf)
    edge_indices = get_edge_indices(wf.edges, wf)
    state['node_indices'] = node_indices
    state['edge_indices'] = edge_indices

    # Serialize
    wf_bytes = dill.dumps(state)
    return wf_bytes

def deserialize_wf(wf_bytes):
    """Reconstruct kale Workflow from serialized version.

    Captures all relevant information about tasks and their connections.
    Does not capture any futures or other transient state.
    Does serialize python function for PythonFunctionTasks.

    Parameters
    ----------
    wf_bytes : str (bytes)

    Returns
    -------
    wf : kale.workflow_objects.Workflow
    """

    # Deserialize
    state = dill.loads(wf_bytes)
    index_dict_sanitized = state.pop('index_dict_sanitized')
    node_indices = state.pop('node_indices')
    edge_indices = state.pop('edge_indices')

    # Reconstruct Tasks
    index_dict = reconstruct_index_dict(index_dict_sanitized)

    # Reconstruct DAG
    nodes = reconstruct_nodes(node_indices, index_dict)
    edges = reconstruct_edges(edge_indices, index_dict)

    # Recreate Workflow
    wf = construct_wf(nodes, edges, **state)

    return wf
