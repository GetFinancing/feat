from feat.test.integration import common
from feat.common.text_helper import format_block
from feat.common import defer
from feat.agents.base import (agent, descriptor, manager, contractor,
                              recipient, replay, document, )


class Interest(contractor.BaseContractor):

    protocol_id = 'spam'


class Initiator(manager.BaseManager):

    protocol_id = 'spam'


@document.register
class Descriptor(descriptor.Descriptor):
    document_type = 'discoverer-agent'


@agent.register('discoverer-agent')
class Agent(agent.BaseAgent):

    @replay.journaled
    def initiate(self, state):
        agent.BaseAgent.initiate(self)
        state.medium.register_interest(contractor.Service(Interest))

    def discover(self):
        return self.discover_service(Initiator)


class ServiceDiscoverySimulation(common.SimulationTest):

    @defer.inlineCallbacks
    def prolog(self):
        setup = format_block("""
        agency = spawn_agency()
        agency.start_agent(descriptor_factory('discoverer-agent'))
        agent1 = _.get_agent()
        agency.start_agent(descriptor_factory('discoverer-agent'))
        agent2 = _.get_agent()
        agency.start_agent(descriptor_factory('discoverer-agent'))

        agent3 = _.get_agent()
        """)
        yield self.process(setup)
        self.agents = list()
        self.agents.append(self.get_local('agent1'))
        self.agents.append(self.get_local('agent2'))
        self.agents.append(self.get_local('agent3'))

    @defer.inlineCallbacks
    def test_service_discovery(self):
        servicies = yield self.agents[0].discover()
        dest = map(lambda x: recipient.IRecipient(x), self.agents)
        self.assertIsInstance(servicies, list)
        self.assertEqual(3, len(servicies))
        for recp in servicies:
            self.assertTrue(recipient.IRecipient.providedBy(recp))
            self.assertTrue(recp in dest)