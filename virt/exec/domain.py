import libvirt

def list(hub):
    '''
    List of the virtual machines
    TODO copy the module doc!
    '''
    cnx = libvirt.open()
    domains = cnx.listAllDomains()
    cnx.close()
    return domains
