# Database Schema

This document outlines the database schema for the wf_makiado project.

## 1. `jobs` Collection

Tracks each request to generate a landing page.

**Schema:**
```json
{
  "job_id": "pk_abc123",
  "status": "in-progress", // (e.g., pending, in-progress, completed, failed)
  "input_parameters": {
    "productName": "FitWatch Pro 2024",
    "productPrice": "299.99",
    "language": "es",
    "...": "..."
  },
  "output_shopify_url": "https://tienda.shopify.com/pages/fitwatch-pro-2024",
  "output_gdrive_url": "https://drive.google.com/...",
  "error_message": null,
  "created_at": "2025-09-01T20:45:00Z",
  "updated_at": "2025-09-01T20:46:00Z"
}
```

## 2. `analytics_events` Collection

Tracks conversion events for each generated page.

**Schema:**
```json
{
  "event_id": "pk_xyz789",
  "job_id": "fk_abc123", // Links to the job that generated the page
  "event_type": "add_to_cart", // (e.g., page_view, add_to_cart, purchase)
  "timestamp": "2025-09-02T10:30:00Z",
  "session_id": "sess_user456",
  "metadata": {
    "path": "/pages/fitwatch-pro-2024",
    "utm_source": "facebook"
  }
}
```
