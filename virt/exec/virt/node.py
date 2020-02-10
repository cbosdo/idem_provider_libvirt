# -*- coding: utf-8 -*-
from xml.etree import ElementTree
import sys


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


async def get_hypervisor(hub):
    '''
    Returns the name of the hypervisor running on this node or ``None``.

    Detected hypervisors:

    - kvm
    - xen

    CLI Example:

    .. code-block:: bash

        salt '*' virt.get_hypervisor
    '''
    # To add a new 'foo' hypervisor, add the _is_foo_hyper function,
    # add 'foo' to the list below and add it to the docstring with a .. versionadded::
    hypervisors = ['kvm', 'xen']
    result = [hyper for hyper in hypervisors if await getattr(sys.modules[__name__], '_is_{}_hyper'.format(hyper))(hub)]
    return result[0] if result else None


async def pool_capabilities(hub, connection=None, username=None, password=None):
    '''
    Return the hypervisor connection storage pool capabilities.

    The returned data are either directly extracted from libvirt or computed.
    In the latter case some pool types could be listed as supported while they
    are not. To distinguish between the two cases, check the value of the ``computed`` property.

    :param connection: libvirt connection URI, overriding defaults
    :param username: username to connect with, overriding defaults
    :param password: password to connect with, overriding defaults

    CLI Example:

    .. code-block:: bash

        salt '*' virt.node.pool_capabilities

    '''
    try:
        conn = await hub.exec.virt.util.get_conn(connection, username, password)
        has_pool_capabilities = bool(getattr(conn, 'getStoragePoolCapabilities', None))
        if has_pool_capabilities:
            caps = ElementTree.fromstring(conn.getStoragePoolCapabilities())
            pool_types = _parse_pools_caps(caps)
        else:
            # Compute reasonable values
            all_hypervisors = ['xen', 'kvm', 'bhyve']
            images_formats = ['none', 'raw', 'dir', 'bochs', 'cloop', 'dmg', 'iso', 'vpc', 'vdi',
                              'fat', 'vhd', 'ploop', 'cow', 'qcow', 'qcow2', 'qed', 'vmdk']
            common_drivers = [
                {
                    'name': 'fs',
                    'default_source_format': 'auto',
                    'source_formats': ['auto', 'ext2', 'ext3', 'ext4', 'ufs', 'iso9660', 'udf', 'gfs', 'gfs2',
                                       'vfat', 'hfs+', 'xfs', 'ocfs2'],
                    'default_target_format': 'raw',
                    'target_formats': images_formats
                },
                {
                    'name': 'dir',
                    'default_target_format': 'raw',
                    'target_formats': images_formats
                },
                {'name': 'iscsi'},
                {'name': 'scsi'},
                {
                    'name': 'logical',
                    'default_source_format': 'lvm2',
                    'source_formats': ['unknown', 'lvm2'],
                },
                {
                    'name': 'netfs',
                    'default_source_format': 'auto',
                    'source_formats': ['auto', 'nfs', 'glusterfs', 'cifs'],
                    'default_target_format': 'raw',
                    'target_formats': images_formats
                },
                {
                    'name': 'disk',
                    'default_source_format': 'unknown',
                    'source_formats': ['unknown', 'dos', 'dvh', 'gpt', 'mac', 'bsd', 'pc98', 'sun', 'lvm2'],
                    'default_target_format': 'none',
                    'target_formats': ['none', 'linux', 'fat16', 'fat32', 'linux-swap', 'linux-lvm',
                                       'linux-raid', 'extended']
                },
                {'name': 'mpath'},
                {
                    'name': 'rbd',
                    'default_target_format': 'raw',
                    'target_formats': []
                },
                {
                    'name': 'sheepdog',
                    'version': 10000,
                    'hypervisors': ['kvm'],
                    'default_target_format': 'raw',
                    'target_formats': images_formats
                },
                {
                    'name': 'gluster',
                    'version': 1002000,
                    'hypervisors': ['kvm'],
                    'default_target_format': 'raw',
                    'target_formats': images_formats
                },
                {'name': 'zfs', 'version': 1002008, 'hypervisors': ['bhyve']},
                {'name': 'iscsi-direct', 'version': 4007000, 'hypervisors': ['kvm', 'xen']}
            ]

            libvirt_version = conn.getLibVersion()
            hypervisor = await hub.exec.virt.node.get_hypervisor()

            def _get_backend_output(backend):
                output = {
                    'name': backend['name'],
                    'supported': (not backend.get('version') or libvirt_version >= backend['version']) and
                        hypervisor in backend.get('hypervisors', all_hypervisors),
                    'options': {
                        'pool': {
                            'default_format': backend.get('default_source_format'),
                            'sourceFormatType': backend.get('source_formats')
                        },
                        'volume': {
                            'default_format': backend.get('default_target_format'),
                            'targetFormatType': backend.get('target_formats')
                        }
                    }
                }

                # Cleanup the empty members to match the libvirt output
                for option_kind in ['pool', 'volume']:
                    if not [value for value in output['options'][option_kind].values() if value is not None]:
                        del output['options'][option_kind]
                if not output['options']:
                    del output['options']

                return output
            pool_types = [_get_backend_output(backend) for backend in common_drivers]
    finally:
        conn.close()

    return {
        'computed': not has_pool_capabilities,
        'pool_types': pool_types,
    }


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


def _parse_pools_caps(doc):
    '''
    Parse libvirt pool capabilities XML
    '''
    def _parse_pool_caps(pool):
        pool_caps = {
            'name': pool.get('type'),
            'supported': pool.get('supported', 'no') == 'yes'
        }
        for option_kind in ['pool', 'vol']:
            options = {}
            default_format_node = pool.find('{0}Options/defaultFormat'.format(option_kind))
            if default_format_node is not None:
                options['default_format'] = default_format_node.get('type')
            options_enums = {enum.get('name'): [value.text for value in enum.findall('value')]
                 for enum in pool.findall('{0}Options/enum'.format(option_kind))}
            if options_enums:
                options.update(options_enums)
            if options:
                if 'options' not in pool_caps:
                    pool_caps['options'] = {}
                kind = option_kind if option_kind is not 'vol' else 'volume'
                pool_caps['options'][kind] = options
        return pool_caps

    return [_parse_pool_caps(pool) for pool in doc.findall('pool')]


async def _is_kvm_hyper(hub):
    '''
    Returns a bool whether or not this node is a KVM hypervisor
    '''
    try:
        with open('/proc/modules') as fp_:
            if 'kvm_' not in fp_.read():
                return False
    except IOError:
        # No /proc/modules? Are we on Windows? Or Solaris?
        return False
    return 'libvirtd' in (await hub.exec.cmd.run(hub.grains.GRAINS['ps']))['stdout']


async def _is_xen_hyper(hub):
    '''
    Returns a bool whether or not this node is a XEN hypervisor
    '''
    try:
        if hub.grains.GRAINS['virtual_subtype'] != 'Xen Dom0':
            return False
    except KeyError:
        # virtual_subtype isn't set everywhere.
        return False
    try:
        with open('/proc/modules') as fp_:
            if 'xen_' not in fp_.read():
                return False
    except (OSError, IOError):
        # No /proc/modules? Are we on Windows? Or Solaris?
        return False
    return 'libvirtd' in (await hub.exec.cmd.run(hub.grains.GRAINS['ps']))['stdout']
