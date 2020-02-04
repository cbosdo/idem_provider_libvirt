def __init__(hub):
    hub.pop.conf.integrate('virt', loader='yaml', cli='virt', roots=True)
    hub.pop.sub.add(dyne_name='exec')
    hub.pop.sub.load_subdirs(hub.exec)
