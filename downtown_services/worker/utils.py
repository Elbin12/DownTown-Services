import stripe
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from django.utils.timezone import make_aware, now


# Subscription management

def get_subscription_details(worker_profile):    
    try:
        worker_subscription = worker_profile.worker_subscription
        if worker_subscription.stripe_subscription_id:
            subscription = stripe.Subscription.retrieve(worker_profile.stripe_subscription_id)
            
            return Response({
                'status': subscription.status,
                'current_period_end': datetime.fromtimestamp(subscription.current_period_end),
                'cancel_at_period_end': subscription.cancel_at_period_end,
                'plan': worker_subscription.tier_name if worker_subscription else None
            })
        
        return Response({'status': 'no_subscription', 'message': 'No active subscription found'})
    except stripe.error.StripeError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def cancel_subscription(worker_profile):
    """Cancel a subscription"""
    try:
        worker_subscription = worker_profile.worker_subscription
        if worker_subscription.stripe_subscription_id:
            subscription = stripe.Subscription.modify(
                worker_subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            worker_subscription.subscription_end_date = datetime.fromtimestamp(subscription.current_period_end)
            worker_subscription.subscription_status = 'canceled'
            worker_subscription.save()

            return True
    except stripe.error.StripeError as e:
        print(f"Error canceling subscription: {str(e)}")
        return False


def check_subscription_status(worker_profile):
    """Check and update subscription status"""
    try:
        worker_subscription = worker_profile.worker_subscription
        if worker_subscription.stripe_subscription_id:
            subscription = stripe.Subscription.retrieve(worker_profile.stripe_subscription_id)
            
            worker_profile.is_subscribed = subscription.status == 'active'
            worker_subscription.subscription_end_date = datetime.fromtimestamp(subscription.current_period_end)
            worker_profile.save()
            
            return subscription.status
        return None
    except stripe.error.StripeError as e:
        print(f"Error checking subscription status: {str(e)}")
        return None


def update_subscription_plan(worker_profile, new_plan):
    try:
        worker_subscription = worker_profile.worker_subscription
        subscription = stripe.Subscription.retrieve(worker_subscription.stripe_subscription_id)

        if not subscription.get('items') or len(subscription['items']['data']) == 0:
            return {"success": False, "message": "No subscription items found."}
        
        subscription_item_id = subscription['items']['data'][0].id  

        subscription = stripe.Subscription.modify(
            worker_subscription.stripe_subscription_id,
            items=[{
                'id': subscription_item_id,
                'price': new_plan.stripe_price_id,
            }],
            expand=['latest_invoice.payment_intent'],
            proration_behavior='none',
            cancel_at_period_end=False,
            billing_cycle_anchor='now', 
        )

        if not subscription:
            return {"success": False, "message": "Subscription update failed. No subscription returned."}
        
        payment_intent = subscription.latest_invoice.payment_intent
        if payment_intent.status != "succeeded":
            return Response({"error": "Payment for the upgrade failed."}, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        subscription_end_date = make_aware(datetime.fromtimestamp(subscription.current_period_end))

        worker_subscription.stripe_price_id = new_plan.stripe_price_id
        worker_subscription.stripe_product_id = new_plan.stripe_product_id

        worker_subscription.tier_name = new_plan.tier_name
        worker_subscription.subscription_status = subscription['status']
        worker_subscription.price=new_plan.price
        worker_subscription.platform_fee_perc=new_plan.platform_fee_perc
        worker_subscription.analytics=new_plan.analytics
        worker_subscription.service_add_limit=new_plan.service_add_limit
        worker_subscription.service_update_limit=new_plan.service_update_limit 
        worker_subscription.user_requests_limit=new_plan.user_requests_limit  
        worker_subscription.subscription_end_date=subscription_end_date  
        worker_subscription.subscription_start_date = now()
        worker_subscription.invoice_id = subscription.latest_invoice.id

        worker_subscription.save()

        return subscription
    except stripe.error.StripeError as e:
        return {"success": False, "message": str(e)}