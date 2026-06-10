"""
Example usage of the AI-Agents framework.
"""

from agents import Agent
from agents.llm import MockProvider, OpenAIProvider


def basic_agent_example():
    """Basic example of creating and using an agent."""
    print("=== Basic Agent Example ===")

    # Create a simple agent
    agent = Agent(name="AssistantAgent", model="gpt-4")

    # Execute a task
    result = agent.execute("What is the capital of France?")
    print(f"Result: {result}")

    # Get agent state
    state = agent.get_state()
    print(f"Agent State: {state}")


def multi_agent_example():
    """Example with multiple agents."""
    print("\n=== Multi-Agent Example ===")

    # Create multiple agents with different roles
    analyzer = Agent(name="DataAnalyzer", model="gpt-4")
    researcher = Agent(name="Researcher", model="gpt-3.5-turbo")
    writer = Agent(name="ContentWriter", model="gpt-4")

    # Execute tasks
    analysis = analyzer.execute("Analyze the provided dataset")
    research = researcher.execute("Research recent trends")
    content = writer.execute("Write an article based on analysis")

    print(f"Analysis: {analysis}")
    print(f"Research: {research}")
    print(f"Content: {content}")


def agent_state_example():
    """Example demonstrating agent state management."""
    print("\n=== Agent State Example ===")

    agent = Agent(name="StatefulAgent")

    # Update agent state
    agent.update_state("memory", ["task1", "task2"])
    agent.update_state("iterations", 0)
    agent.update_state("status", "active")

    # Get and display state
    state = agent.get_state()
    print(f"Agent Name: {state['name']}")
    print(f"Custom State: {state['state']}")


def llm_provider_example():
    """Example demonstrating LLM provider usage."""
    print("\n=== LLM Provider Example ===")

    # Using Mock provider for testing
    mock_provider = MockProvider()
    response = mock_provider.generate("Tell me a joke")
    print(f"Mock Provider Response: {response}")

    # Using OpenAI provider (would use real API key in production)
    openai_provider = OpenAIProvider(model="gpt-4")
    response = openai_provider.generate("How does machine learning work?")
    print(f"OpenAI Provider Response: {response}")


if __name__ == "__main__":
    print("AI-Agents Framework Examples\n")

    try:
        basic_agent_example()
        multi_agent_example()
        agent_state_example()
        llm_provider_example()

        print("\n✅ All examples completed successfully!")
    except Exception as e:
        print(f"❌ Error running examples: {e}")

