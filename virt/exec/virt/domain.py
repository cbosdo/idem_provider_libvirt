# -*- coding: utf-8 -*-
import datetime
import json
import re
import subprocess
from xml.etree import ElementTree

try:
    import libvirt  # pylint: disable=import-error
    from libvirt import libvirtError
    HAS_LIBVIRT = True
except ImportError:
    HAS_LIBVIRT = False

VIRT_STATE_NAME_MAP = {0: 'running',
                       1: 'running',
                       2: 'running',
                       3: 'paused',
                       4: 'shutdown',
                       5: 'shutdown',
                       6: 'crashed'}


#def __virtual__():
#    if not HAS_LIBVIRT:
#        return (False, 'Unable to locate or import python libvirt library.')
#    return 'virt'

async def list_all(hub, connection=None, username=None, password=None):
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

        salt '*' virt.list
    '''
    vms = []
    conn = await hub.exec.virt.util.get_conn(connection, username, password)
    try:
        for dom in _get_domain(conn, iterable=True):
            vms.append(dom.name())
    finally:
        conn.close()
    return vms


async def list_active(hub, connection=None, username=None, password=None):
    '''
    Return a list of names for active virtual machine on the minion

    :param connection: libvirt connection URI, overriding defaults
    :param username: username to connect with, overriding defaults
    :param password: password to connect with, overriding defaults

    CLI Example:

    .. code-block:: bash

        salt '*' virt.list_active
    '''
    vms = []
    conn = await hub.exec.virt.util.get_conn(connection, username, password)
    try:
        for dom in _get_domain(conn, iterable=True, inactive=False):
            vms.append(dom.name())
    finally:
        conn.close()
    return vms


async def list_inactive(hub, connection=None, username=None, password=None):
    '''
    Return a list of names for inactive virtual machine on the minion

    :param connection: libvirt connection URI, overriding defaults
    :param username: username to connect with, overriding defaults
    :param password: password to connect with, overriding defaults

    CLI Example:

    .. code-block:: bash

        salt '*' virt.list_inactive
    '''
    vms = []
    conn = await hub.exec.virt.util.get_conn(connection, username, password)
    try:
        for dom in _get_domain(conn, iterable=True, active=False):
            vms.append(dom.name())
    finally:
        conn.close()
    return vms


async def get_xml(hub, vm_, connection=None, username=None, password=None):
    '''
    Returns the XML for a given vm

    :param vm_: domain name
    :param connection: libvirt connection URI, overriding defaults
    :param username: username to connect with, overriding defaults
    :param password: password to connect with, overriding defaults

    CLI Example:

    .. code-block:: bash

        salt '*' virt.domain.get_xml <domain>
    '''
    conn = await hub.exec.virt.util.get_conn(connection, username, password)
    try:
        xml_desc = vm_.XMLDesc(0) if isinstance(
            vm_, libvirt.virDomain
        ) else _get_domain(conn, vm_).XMLDesc(0)
    finally:
        conn.close()
    return xml_desc


async def info(hub, vm_=None, connection=None, username=None, password=None):
    '''
    Return detailed information about the vms on this hyper in a
    list of dicts:

    :param vm_: name of the domain
    :param connection: libvirt connection URI, overriding defaults
    :param username: username to connect with, overriding defaults
    :param password: password to connect with, overriding defaults

    .. code-block:: python

        [
            'your-vm': {
                'cpu': <int>,
                'maxMem': <int>,
                'mem': <int>,
                'state': '<state>',
                'cputime' <int>
                },
            ...
            ]

    If you pass a VM name in as an argument then it will return info
    for just the named VM, otherwise it will return all VMs.

    CLI Example:

    .. code-block:: bash

        salt '*' virt.domain.info
    '''
    def _info(dom):
        '''
        Compute the infos of a domain
        '''
        raw = dom.info()
        return {'cpu': raw[3],
                'cputime': int(raw[4]),
                'disks': _get_disks(dom),
                'graphics': _get_graphics(dom),
                'nics': _get_nics(dom),
                'uuid': _get_uuid(dom),
                'on_crash': _get_on_crash(dom),
                'on_reboot': _get_on_reboot(dom),
                'on_poweroff': _get_on_poweroff(dom),
                'maxMem': int(raw[1]),
                'mem': int(raw[2]),
                'state': VIRT_STATE_NAME_MAP.get(raw[0], 'unknown')}
    info = {}
    conn = await hub.exec.virt.util.get_conn(connection, username, password)
    try:
        if vm_:
            info[vm_] = _info(_get_domain(conn, vm_))
        else:
            for domain in _get_domain(conn, iterable=True):
                info[domain.name()] = _info(domain)
    finally:
        conn.close()
    return info


async def state(hub, vm_=None, connection=None, username=None, password=None):
    '''
    Return list of all the vms and their state.

    If you pass a VM name in as an argument then it will return info
    for just the named VM, otherwise it will return all VMs.

    :param vm_: name of the domain
    :param connection: libvirt connection URI, overriding defaults
    :param username: username to connect with, overriding defaults
    :param password: password to connect with, overriding defaults

    CLI Example:

    .. code-block:: bash

        salt '*' virt.domain.state <domain>
    '''
    def _info(dom):
        '''
        Compute domain state
        '''
        state = ''
        raw = dom.info()
        state = VIRT_STATE_NAME_MAP.get(raw[0], 'unknown')
        return state
    info = {}
    conn = await hub.exec.virt.util.get_conn(connection, username, password)
    try:
        if vm_:
            info[vm_] = _info(_get_domain(conn, vm_))
        else:
            for domain in _get_domain(conn, iterable=True):
                info[domain.name()] = _info(domain)
    finally:
        conn.close()
    return info


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


def _get_uuid(dom):
    '''
    Return a uuid from the named vm

    CLI Example:

    .. code-block:: bash

        salt '*' virt.get_uuid <domain>
    '''
    return ElementTree.fromstring(dom.XMLDesc(0)).find('uuid').text


def _get_nics(dom):
    '''
    Get domain network interfaces from a libvirt domain object.
    '''
    nics = {}
    doc = ElementTree.fromstring(dom.XMLDesc(0))
    for iface_node in doc.findall('devices/interface'):
        nic = {}
        nic['type'] = iface_node.get('type')
        for v_node in iface_node:
            if v_node.tag == 'mac':
                nic['mac'] = v_node.get('address')
            if v_node.tag == 'model':
                nic['model'] = v_node.get('type')
            if v_node.tag == 'target':
                nic['target'] = v_node.get('dev')
            # driver, source, and match can all have optional attributes
            if re.match('(driver|source|address)', v_node.tag):
                temp = {}
                for key, value in v_node.attrib.items():
                    temp[key] = value
                nic[v_node.tag] = temp
            # virtualport needs to be handled separately, to pick up the
            # type attribute of the virtualport itself
            if v_node.tag == 'virtualport':
                temp = {}
                temp['type'] = v_node.get('type')
                for key, value in v_node.attrib.items():
                    temp[key] = value
                nic['virtualport'] = temp
        if 'mac' not in nic:
            continue
        nics[nic['mac']] = nic
    return nics


def _get_graphics(dom):
    '''
    Get domain graphics from a libvirt domain object.
    '''
    out = {'autoport': 'None',
           'keymap': 'None',
           'listen': 'None',
           'port': 'None',
           'type': 'None'}
    doc = ElementTree.fromstring(dom.XMLDesc(0))
    for g_node in doc.findall('devices/graphics'):
        for key, value in g_node.attrib.items():
            out[key] = value
    return out


def _parse_qemu_img_info(info):
    '''
    Parse qemu-img info JSON output into disk infos dictionary
    '''
    raw_infos = json.loads(info)
    disks = []
    for disk_infos in raw_infos:
        disk = {
                   'file': disk_infos['filename'],
                   'file format': disk_infos['format'],
                   'disk size': disk_infos['actual-size'],
                   'virtual size': disk_infos['virtual-size'],
                   'cluster size': disk_infos['cluster-size'] if 'cluster-size' in disk_infos else None,
               }

        if 'full-backing-filename' in disk_infos.keys():
            disk['backing file'] = format(disk_infos['full-backing-filename'])

        if 'snapshots' in disk_infos.keys():
            disk['snapshots'] = [
                    {
                        'id': snapshot['id'],
                        'tag': snapshot['name'],
                        'vmsize': snapshot['vm-state-size'],
                        'date': datetime.datetime.fromtimestamp(
                            float('{}.{}'.format(snapshot['date-sec'], snapshot['date-nsec']))).isoformat(),
                        'vmclock': datetime.datetime.utcfromtimestamp(
                            float('{}.{}'.format(snapshot['vm-clock-sec'],
                                                 snapshot['vm-clock-nsec']))).time().isoformat()
                    } for snapshot in disk_infos['snapshots']]
        disks.append(disk)

    for disk in disks:
        if 'backing file' in disk.keys():
            candidates = [info for info in disks if 'file' in info.keys() and info['file'] == disk['backing file']]
            if candidates:
                disk['backing file'] = candidates[0]

    return disks[0]


def _get_disks(dom):
    '''
    Get domain disks from a libvirt domain object.
    '''
    disks = {}
    doc = ElementTree.fromstring(dom.XMLDesc(0))
    for elem in doc.findall('devices/disk'):
        source = elem.find('source')
        if source is None:
            continue
        target = elem.find('target')
        if target is None:
            continue
        if 'dev' in target.attrib:
            qemu_target = source.get('file', '')
            if not qemu_target:
                qemu_target = source.get('dev', '')
            if not qemu_target and 'protocol' in source.attrib and 'name' in source.attrib:  # for rbd network
                qemu_target = '{0}:{1}'.format(
                        source.get('protocol'),
                        source.get('name'))
            if not qemu_target:
                continue

            disk = {'file': qemu_target, 'type': elem.get('device')}

            driver = elem.find('driver')
            if driver is not None and driver.get('type') == 'qcow2':
                try:
                    stdout = subprocess.Popen(
                                ['qemu-img', 'info', '-U', '--output', 'json', '--backing-chain', disk['file']],
                                shell=False,
                                stdout=subprocess.PIPE).communicate()[0]
                    output = _parse_qemu_img_info(stdout.decode())
                    disk.update(output)
                except TypeError:
                    disk.update({'file': 'Does not exist'})

            disks[target.get('dev')] = disk
    return disks


def _get_on_poweroff(dom):
    '''
    Return `on_poweroff` setting from the named vm
    '''
    node = ElementTree.fromstring(dom.XMLDesc(0)).find('on_poweroff')
    return node.text if node is not None else ''


def _get_on_reboot(dom):
    '''
    Return `on_reboot` setting from the named vm
    '''
    node = ElementTree.fromstring(dom.XMLDesc(0)).find('on_reboot')
    return node.text if node is not None else ''


def _get_on_crash(dom):
    '''
    Return `on_crash` setting from the named vm
    '''
    node = ElementTree.fromstring(dom.XMLDesc(0)).find('on_crash')
    return node.text if node is not None else ''
