# Fulfillment Operations Playbook

## Late shipment escalation

If a shipment misses its planned carrier scan by more than 24 hours, the case owner should:

1. Confirm the warehouse handoff timestamp in the order system.
2. Contact the carrier support desk with the order number and tracking number.
3. Post an update in the `fulfillment-ops` channel for orders above $500.
4. Escalate to the regional operations lead if the shipment remains unscanned for 48 hours.

Priority orders should be escalated immediately after the carrier check, without waiting for the 48-hour mark.

## Incident severity targets

Priority one incidents are issues that stop order creation, fulfillment release, or payment capture for more than one region.

- Acknowledge within 15 minutes.
- Assign an incident owner within 20 minutes.
- Provide the first internal status update within 30 minutes.
- Publish updates every 30 minutes until service is restored.

## Returns processing

Returned items should be routed to the Austin returns hub unless the item is classified as hazardous. Hazardous returns are routed through the vendor recovery workflow.

