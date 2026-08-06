from typing import List, Dict, Any, Optional

class PromptTemplates:
    """Prompt templates for different RAG scenarios"""
    
    # System prompts
    SYSTEM_PROMPT = """You are a helpful IT Helpdesk Assistant with expertise in technical support, 
    system administration, and troubleshooting. Your goal is to provide accurate, clear, and actionable 
    solutions to IT-related problems.
    
    Guidelines:
    1. Be professional and courteous
    2. Provide step-by-step solutions when applicable
    3. Use the provided context to answer questions accurately
    4. If you don't know the answer, admit it and suggest alternatives
    5. Use plain language and avoid unnecessary jargon
    6. Ask clarifying questions if the problem is unclear
    7. Always prioritize security best practices
    8. Document your reasoning process briefly
    
    You are an AI assistant designed to help with:
    - Hardware and software troubleshooting
    - Network and connectivity issues
    - Account and access management
    - Security concerns and best practices
    - System administration tasks
    - General IT questions and guidance"""
    
    # User prompt templates
    CHAT_TEMPLATE = """Current conversation context:
    {context}
    
    User query: {query}
    
    Relevant documents from knowledge base:
    {retrieved_context}
    
    Provide a helpful, accurate, and actionable response to the user's IT helpdesk query:"""
    
    TICKET_SUMMARY_TEMPLATE = """Based on the following conversation, create a concise ticket summary:
    
    Conversation:
    {conversation}
    
    Ticket details:
    - Title: {title}
    - Description: {description}
    - Priority: {priority}
    - Category: {category}
    
    Provide a summary of the issue and recommended solution:"""
    
    TICKET_CLASSIFICATION_TEMPLATE = """Classify the following IT support ticket:
    
    Subject: {subject}
    Description: {description}
    
    Provide classification in JSON format:
    {{
        "category": "hardware|software|network|security|account|other",
        "priority": "low|medium|high|critical",
        "estimated_effort": "low|medium|high",
        "suggested_assignee": "team_name",
        "related_issues": ["issue1", "issue2"],
        "suggested_solution": "Brief solution description"
    }}"""
    
    KNOWLEDGE_EXTRACTION_TEMPLATE = """Extract key information from the following IT documentation:
    
    Document:
    {document}
    
    Extract and structure the following information:
    - Main topics covered
    - Step-by-step procedures
    - Troubleshooting steps
    - Error messages and solutions
    - Security considerations
    - Dependencies and requirements
    
    Provide structured output in JSON format:"""
    
    SECURITY_AUDIT_TEMPLATE = """Analyze the following security-related query or action:
    
    Action: {action}
    User: {user}
    Context: {context}
    
    Security Assessment:
    - Risk Level: (low/medium/high/critical)
    - Compliance Impact: (none/minor/major)
    - Recommended Actions:
    - Potential Threats:
    - Mitigation Strategies:"""
    
    def get_chat_prompt(self, query: str, retrieved_context: str, context: str = "") -> str:
        """Get formatted chat prompt"""
        return self.CHAT_TEMPLATE.format(
            query=query,
            retrieved_context=retrieved_context,
            context=context
        )
    
    def get_ticket_summary_prompt(
        self,
        conversation: str,
        title: str,
        description: str,
        priority: str,
        category: str
    ) -> str:
        """Get formatted ticket summary prompt"""
        return self.TICKET_SUMMARY_TEMPLATE.format(
            conversation=conversation,
            title=title,
            description=description,
            priority=priority,
            category=category
        )
    
    def get_classification_prompt(self, subject: str, description: str) -> str:
        """Get formatted ticket classification prompt"""
        return self.TICKET_CLASSIFICATION_TEMPLATE.format(
            subject=subject,
            description=description
        )
    
    def get_knowledge_extraction_prompt(self, document: str) -> str:
        """Get formatted knowledge extraction prompt"""
        return self.KNOWLEDGE_EXTRACTION_TEMPLATE.format(document=document)
    
    def get_security_audit_prompt(self, action: str, user: str, context: str) -> str:
        """Get formatted security audit prompt"""
        return self.SECURITY_AUDIT_TEMPLATE.format(
            action=action,
            user=user,
            context=context
        )
    
    @staticmethod
    def format_retrieved_context(documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into context string"""
        if not documents:
            return "No relevant documents found."
        
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            source = metadata.get('source', f'Document {i}')
            
            context_parts.append(f"[Document {i}] from {source}:\n{content}\n")
        
        return "\n".join(context_parts)
    
    @staticmethod
    def format_conversation_history(messages: List[Dict[str, str]]) -> str:
        """Format conversation history for context"""
        history_parts = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_parts.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(history_parts)