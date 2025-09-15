from llama_index.core.prompts import ChatMessage, MessageRole

def get_user_prompt() -> ChatMessage:
    """
    Returns a user prompt template for injecting user input into the chat context.

    The placeholder {input} should be replaced with the actual user question.
    """
    return ChatMessage(role=MessageRole.USER, content="Question: {input}")
