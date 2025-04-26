# Prompt Engineering Strategy for AMO Events Knowledge Base

## Overview

This document outlines the prompt engineering strategies used in the AMO Events knowledge base to ensure accurate, relevant, and helpful responses to user queries. Effective prompt engineering is critical for maximizing the utility of our LLM-powered knowledge base, particularly when working with domain-specific information about event management platforms.

## Core Principles

1. **Context Preservation**: Ensure that follow-up questions maintain previous conversation context
2. **Precision Over Generality**: Optimize for specific, accurate answers rather than general information
3. **Knowledge Grounding**: All responses should be grounded in our knowledge base, not LLM general knowledge
4. **Transparency**: Clearly indicate when information is uncertain or outside our knowledge base
5. **Actionability**: Focus on providing actionable guidance that users can immediately apply

## Prompt Components

### System Prompts

Our system prompts define the assistant's role and rules of engagement:

```
You are an AI assistant for the AMO Events platform, which helps event organizers use Webflow, Airtable, and other tools to create and manage events. 
Answer questions based ONLY on the provided context. If you don't have enough information in the context, acknowledge this limitation and suggest the user rephrase or ask a more specific question.
Always cite your sources by indicating which documents provided the information.
```

### Query Reformulation

We use query reformulation techniques to improve retrieval performance:

1. **Query Expansion**: Add relevant terms to improve search results
   ```python
   def expand_query(original_query):
       # Add synonyms and related terms to improve retrieval
       expansions = {
           "registration": ["sign-up", "RSVP", "registration form"],
           "attendee": ["guest", "participant", "visitor"],
           # More expansions...
       }
       # Implementation details
   ```

2. **Query Decomposition**: Break complex queries into simpler sub-queries
   ```python
   def decompose_query(complex_query):
       # Split multi-part questions to ensure all parts are addressed
       # Implementation details
   ```

### Context Window Management

For longer conversations, we implement strategic context management:

1. **Summarization**: Periodically summarize conversation to preserve tokens
2. **Key Information Retention**: Prioritize keeping important details from earlier exchanges
3. **Recency Bias**: Weight recent exchanges more heavily than older ones

## Fallback Strategies

When the knowledge base cannot answer a query, we implement staged fallbacks:

1. **Acknowledgment**: Clearly state that the information isn't available
2. **Suggestion**: Offer to reformulate the query or suggest related topics
3. **Redirection**: Provide guidance on where to find information outside the system

Example fallback template:
```
I don't have specific information about [topic] in my knowledge base. 

This might be because:
- The topic is very recent or not covered in my training data
- The question needs to be more specific
- This is outside the scope of AMO Events platform knowledge

You might try:
- Rephrasing your question with more specific details
- Asking about [related_topic1] or [related_topic2] instead
- Consulting the official documentation at [relevant_url]
```

## Prompt Templates by Query Type

### How-To Queries

For procedural questions about completing tasks:

```
Based on the provided information, here are the steps to [task]:

1. First, [step1]
2. Next, [step2]
3. Finally, [step3]

This information comes from [source].
```

### Comparison Queries

For questions comparing features or approaches:

```
When comparing [optionA] and [optionB] for [purpose]:

[OptionA]:
- Advantage: [advantageA1]
- Advantage: [advantageA2]
- Limitation: [limitationA1]

[OptionB]:
- Advantage: [advantageB1]
- Advantage: [advantageB2]
- Limitation: [limitationB1]

For your specific case of [context], [recommendation].

Sources: [sourceA], [sourceB]
```

### Troubleshooting Queries

For helping users diagnose and fix problems:

```
The issue with [problem] might be caused by:

1. [PossibleCause1]: [explanation1]
   Solution: [solution1]

2. [PossibleCause2]: [explanation2]
   Solution: [solution2]

To prevent this in the future, consider [preventativeMeasure].

This information is based on [source].
```

## Continuous Improvement

Our prompt engineering is iteratively improved through:

1. **Query Log Analysis**: Regular review of failed and successful queries
2. **A/B Testing**: Testing alternative prompt formulations for key query types
3. **User Feedback**: Incorporating direct user feedback on response quality
4. **Performance Metrics**: Tracking and optimizing for metrics like relevance scores and time-to-resolution

## Example Transformation

Original query:
```
How do I set up Webflow for my event?
```

Transformed effective prompt:
```
Based on the retrieved context documents, provide a step-by-step guide on how to set up Webflow specifically for event registration and management in the AMO Events platform. Include initial setup, form creation, and integration with other tools if that information is available in the provided context. If specific details are missing, acknowledge the limitations of the available information.
```

## Knowledge Gap Handling

When knowledge gaps are identified:

1. Document the gap in our logging system
2. Provide the most helpful general guidance possible
3. Suggest alternative approaches when available
4. Add the topic to our content roadmap for future knowledge base updates

## Appendix: Prompt Engineering Checklist

Before deploying new prompt templates, verify that they:

- [ ] Maintain conversation context across multiple turns
- [ ] Clearly distinguish between retrieved facts and generated content
- [ ] Provide appropriate levels of detail based on query complexity
- [ ] Handle edge cases (ambiguity, out-of-scope questions, etc.)
- [ ] Support source attribution
- [ ] Balance brevity with completeness
- [ ] Use appropriate formatting for readability 