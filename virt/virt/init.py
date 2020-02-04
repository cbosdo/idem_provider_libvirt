def __init__(hub):
    hub.virt.CONS = {}
    hub.pop.conf.integrate('virt', cli='virt', roots=True)
    hub.pop.sub.add(dyne_name='exec')
    hub.virt.exec.domain.list()
