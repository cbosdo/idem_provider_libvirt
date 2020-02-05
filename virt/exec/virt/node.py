# -*- coding: utf-8 -*-


async def info(hub, connection=None, username=None, password=None):
    '''
    Return a dict with information about this node

    :param connection: libvirt connection URI, overriding defaults
    :param username: username to connect with, overriding defaults
    :param password: password to connect with, overriding defaults

    CLI Example:

    .. code-block:: bash

        salt '*' virt.node.info
    '''
    conn = await hub.exec.virt.util.get_conn(connection, username, password)
    try:
        info = _node_info(conn)
    finally:
        conn.close()
    return info


def _node_info(conn):
    '''
    Internal variant of node_info taking a libvirt connection as parameter
    '''
    raw = conn.getInfo()
    info = {'cpucores': raw[6],
            'cpumhz': raw[3],
            'cpumodel': raw[0],
            'cpus': raw[2],
            'cputhreads': raw[7],
            'numanodes': raw[4],
            'phymemory': raw[1],
            'sockets': raw[5]}
    return info
