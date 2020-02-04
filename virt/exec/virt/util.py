import libvirt
import logging

log = logging.getLogger(__name__)

def __get_request_auth(hub, username, password):
    '''
    Get libvirt.openAuth callback with username, password values overriding
    the configuration ones.
    '''

    # pylint: disable=unused-argument
    def __request_auth(credentials, user_data):
        '''Callback method passed to libvirt.openAuth().

        The credentials argument is a list of credentials that libvirt
        would like to request. An element of this list is a list containing
        5 items (4 inputs, 1 output):
          - the credential type, e.g. libvirt.VIR_CRED_AUTHNAME
          - a prompt to be displayed to the user
          - a challenge
          - a default result for the request
          - a place to store the actual result for the request

        The user_data argument is currently not set in the openAuth call.
        '''
        for credential in credentials:
            if credential[0] == libvirt.VIR_CRED_AUTHNAME:
                credential[4] = username if username else hub.OPT['virt'].get('username', credential[3])
            elif credential[0] == libvirt.VIR_CRED_NOECHOPROMPT:
                credential[4] = password if password else hub['virt'].get('username', credential[3])
            else:
                log.info('Unhandled credential type: %s', credential[0])
        return 0


async def get_conn(hub, connection=None, username=None, password=None):
    '''
    Detects what type of dom this node is and attempts to connect to the
    correct hypervisor via libvirt.

    :param connection: libvirt connection URI, overriding defaults
    :param username: username to connect with, overriding defaults
    :param password: password to connect with, overriding defaults

    '''
    conn_str = connection or hub.OPT['virt']['uri']

    try:
        auth_types = [libvirt.VIR_CRED_AUTHNAME,
                      libvirt.VIR_CRED_NOECHOPROMPT,
                      libvirt.VIR_CRED_ECHOPROMPT,
                      libvirt.VIR_CRED_PASSPHRASE,
                      libvirt.VIR_CRED_EXTERNAL]
        conn = libvirt.openAuth(conn_str, [auth_types, __get_request_auth(hub, username, password), None], 0)
    except Exception:  # pylint: disable=broad-except
        raise Exception(
            'Sorry, failed to open a connection to the hypervisor software at {0}'.format(conn_str)
        )
    return conn
