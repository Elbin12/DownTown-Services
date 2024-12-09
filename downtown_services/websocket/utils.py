
from accounts.models import ChatMessage
from django.db.models import Q, OuterRef, Subquery


def RecentChats(sender_id, sender_type):
    # Import serializers at the top level for clarity
    from accounts.serializer import ChatMessageSerializer as UserChatMessageSerializer
    from worker.serializer import ChatMessageSerializer as WorkerChatMessageSerializer

    # Use the appropriate serializer based on sender type
    ChatMessageSerializer = (
        UserChatMessageSerializer if sender_type == 'user' else WorkerChatMessageSerializer
    )

    # Subquery to fetch the latest message ID for each conversation
    last_message_subquery = ChatMessage.objects.filter(
        Q(sender_id=OuterRef('sender_id'), recipient_id=OuterRef('recipient_id')) |
        Q(sender_id=OuterRef('recipient_id'), recipient_id=OuterRef('sender_id'))
    ).filter(
        Q(sender_id=sender_id) | Q(recipient_id=sender_id)  # Restrict to user's conversations
    ).order_by('-timestamp').values('id')[:1]

    # Main query to fetch the latest messages in user's conversations
    last_messages = ChatMessage.objects.filter(
        Q(sender_id=sender_id) | Q(recipient_id=sender_id),  # Include only user's messages
        id__in=Subquery(last_message_subquery)
    ).order_by('-timestamp')

    # Serialize the results
    serializer = ChatMessageSerializer(last_messages, many=True)
    
    # Log and return serialized data
    print(sender_type, serializer.data, 'from function')
    return serializer.data
