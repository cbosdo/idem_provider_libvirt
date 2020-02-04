# -*- coding: utf-8 -*-

try:
    import libvirt  # pylint: disable=import-error
    from libvirt import libvirtError
    HAS_LIBVIRT = True
except ImportError:
    HAS_LIBVIRT = False

#def __virtual__():
#    if not HAS_LIBVIRT:
#        return (False, 'Unable to locate or import python libvirt library.')
#    return 'virt'

def list(hub, connection=None, username=None, password=None):
    '''
    Return a list of available domains.

    :param connection: libvirt connection URI, overriding defaults

        .. versionadded:: 2019.2.0
    :param username: username to connect with, overriding defaults

        .. versionadded:: 2019.2.0
    :param password: password to connect with, overriding defaults

        .. versionadded:: 2019.2.0

    CLI Example:

    .. code-block:: bash

        salt '*' virt.list_domains
    '''
    vms = []
    conn = await hub.exec.virt.util.get_conn(connection, username, password)
    try:
        for dom in _get_domain(conn, iterable=True):
            vms.append(dom.name())
    finally:
        conn.close()
    return vms


def _get_domain(conn, *vms, iterable=False, active=True, inactive=True):
    '''
    Return a domain object for the named VM or return domain object for all VMs.

    :params conn: libvirt connection object
    :param vms: list of domain names to look for
    :param active: True to get the active VMs, false otherwise. Default: True
    :param inactive: True to get the inactive VMs, false otherwise. Default: True
    :param iterable: True to return an array in all cases
    '''
    ret = list()
    lookup_vms = list()

    all_vms = []
    if active:
        for id_ in conn.listDomainsID():
            all_vms.append(conn.lookupByID(id_).name())

    if inactive:
        for id_ in conn.listDefinedDomains():
            all_vms.append(id_)

    if not all_vms:
        raise Exception('No virtual machines found.')

    if vms:
        for name in vms:
            if name not in all_vms:
                raise Exception('The VM "{name}" is not present'.format(name=name))
            else:
                lookup_vms.append(name)
    else:
        lookup_vms = list(all_vms)

    for name in lookup_vms:
        ret.append(conn.lookupByName(name))

    return len(ret) == 1 and not iterable and ret[0] or ret
