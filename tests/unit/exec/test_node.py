# Import python libs
from unittest.mock import patch, mock_open, MagicMock
import pytest

# Import local libs
import virt.exec.virt.node

# Import pop libs
import pop.hub
import pop.mods.pop.testing as testing

class TestExecVirtNode:
    @pytest.mark.asyncio
    async def test_info(self, mock_hub: testing.MockHub, mock_libvirt_conn):
        mock_libvirt_conn.getInfo.return_value = ['x86_64', 4096, 8, 2712, 1, 2, 4, 2]

        actual = await virt.exec.virt.node.info(mock_hub)

        assert 4 == actual['cpucores']
        assert 2712 == actual['cpumhz']
        assert 'x86_64' == actual['cpumodel']
        assert 8 == actual['cpus']
        assert 2 == actual['cputhreads']
        assert 1 == actual['numanodes']
        assert 4096 == actual['phymemory']
        assert 2 == actual['sockets']

    @pytest.mark.asyncio
    async def test_get_hypervisor(self, mock_hub: testing.MockHub):
        # KVM test case
        with patch("builtins.open", mock_open(read_data='kvm_virtio')) as mock_file:
            mock_hub.grains.GRAINS = { 'ps': 'fakeps' }
            mock_hub.exec.cmd.run.return_value = {'stdout': 'libvirtd is running'}
            assert await virt.exec.virt.node.get_hypervisor(mock_hub) == 'kvm'

        # Xen test case
        with patch("builtins.open", mock_open(read_data='xen_blk')) as mock_file:
            mock_hub.grains.GRAINS = {'ps': 'fakeps', 'virtual_subtype': 'Xen Dom0'}
            mock_hub.exec.cmd.run.return_value = {'stdout': 'libvirtd is running'}
            assert await virt.exec.virt.node.get_hypervisor(mock_hub) == 'xen'

        # No running libvirtd test case
        with patch("builtins.open", mock_open(read_data='xen_blk')) as mock_file:
            mock_hub.grains.GRAINS = {'ps': 'fakeps', 'virtual_subtype': 'Xen Dom0'}
            mock_hub.exec.cmd.run.return_value = {'stdout': ''}
            assert await virt.exec.virt.node.get_hypervisor(mock_hub) is None
