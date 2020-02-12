# -*- coding: utf-8 -*-
'''
    tests.unit.conftest
    ~~~~~~~~~~~~~~

    Provide mock_hub fixture for all unit tests.
'''

import sys
import unittest.mock as mock

import pytest

import pop.hub
import pop.mods.pop.testing as testing


@pytest.fixture('session')
def _hub():
    # provides a full hub that is used as a reference by mock_hub
    hub = pop.hub.Hub()
    hub.pop.sub.add(dyne_name='grains')
    hub.grains.GRAINS = {}

    with mock.patch.object(sys, 'argv', sys.argv[:1]):
        hub.pop.sub.add('virt.virt')

    return hub


@pytest.fixture
def mock_hub(_hub, mock_libvirt_conn):
    mocked = testing.MockHub(_hub)
    mocked.exec.virt.util.get_conn.return_value = mock_libvirt_conn
    return mocked


class LibvirtMock(mock.MagicMock):
    class libvirtError(Exception):
        '''
        libvirtError mock
        '''

@pytest.fixture(scope="session")
def mock_libvirt_conn():
    mock_libvirt = LibvirtMock()
    mock_conn = mock.MagicMock()
    mock_libvirt.openAuth.return_value = mock_conn
    sys.modules['libvirt'] = mock_libvirt
    return mock_conn
