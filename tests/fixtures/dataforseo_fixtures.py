"""Mock DataForSEO API responses for unit tests."""

LOCATIONS_RESPONSE = {
    "version": "0.1",
    "status_code": 20000,
    "status_message": "Ok.",
    "tasks": [
        {
            "id": "task-001",
            "status_code": 20000,
            "result": [
                {
                    "location_code": 1012873,
                    "location_name": "Phoenix, Arizona, United States",
                    "location_type": "City",
                    "country_iso_code": "US",
                },
                {
                    "location_code": 1012938,
                    "location_name": "Tucson, Arizona, United States",
                    "location_type": "City",
                    "country_iso_code": "US",
                },
            ],
        }
    ],
    "tasks_count": 1,
    "tasks_error": 0,
}

SERP_TASK_POST_RESPONSE = {
    "version": "0.1",
    "status_code": 20000,
    "status_message": "Ok.",
    "tasks": [
        {
            "id": "task-serp-001",
            "status_code": 20100,
            "status_message": "Task Created.",
            "cost": 0.0006,
        }
    ],
    "tasks_count": 1,
    "tasks_error": 0,
}

SERP_TASK_GET_RESPONSE = {
    "version": "0.1",
    "status_code": 20000,
    "status_message": "Ok.",
    "tasks": [
        {
            "id": "task-serp-001",
            "status_code": 20000,
            "status_message": "Ok.",
            "cost": 0.0006,
            "result": [
                {
                    "keyword": "plumber",
                    "type": "organic",
                    "se_domain": "google.com",
                    "location_code": 1012873,
                    "check_url": "https://www.google.com/search?q=plumber&...",
                    "items_count": 10,
                    "items": [
                        {
                            "type": "organic",
                            "rank_group": 1,
                            "rank_absolute": 1,
                            "domain": "yelp.com",
                            "title": "Top 10 Best Plumbers in Phoenix, AZ",
                            "url": "https://www.yelp.com/search?cflt=plumbing&find_loc=Phoenix",
                        },
                        {
                            "type": "organic",
                            "rank_group": 2,
                            "rank_absolute": 2,
                            "domain": "joesplumbing.com",
                            "title": "Joe's Plumbing - Phoenix AZ",
                            "url": "https://joesplumbing.com",
                        },
                    ],
                }
            ],
        }
    ],
    "tasks_count": 1,
    "tasks_error": 0,
}

SERP_TASK_PENDING_RESPONSE = {
    "version": "0.1",
    "status_code": 20000,
    "status_message": "Ok.",
    "tasks": [
        {
            "id": "task-serp-001",
            "status_code": 20100,
            "status_message": "Task Created.",
        }
    ],
    "tasks_count": 1,
    "tasks_error": 0,
}

BUSINESS_LISTINGS_RESPONSE = {
    "version": "0.1",
    "status_code": 20000,
    "status_message": "Ok.",
    "tasks": [
        {
            "id": "task-biz-001",
            "status_code": 20000,
            "cost": 0.016,
            "result": [
                {
                    "total_count": 20,
                    "items": [
                        {
                            "title": "Joe's Plumbing",
                            "domain": "joesplumbing.com",
                            "phone": "+16025551234",
                            "rating": {"value": 4.5, "votes_count": 89},
                        },
                    ],
                }
            ],
        }
    ],
    "tasks_count": 1,
    "tasks_error": 0,
}

SERP_LIVE_RESPONSE = {
    "version": "0.1",
    "status_code": 20000,
    "status_message": "Ok.",
    "tasks": [
        {
            "id": "task-serp-live-001",
            "status_code": 20000,
            "status_message": "Ok.",
            "cost": 0.002,
            "result": [
                {
                    "keyword": "plumber",
                    "type": "organic",
                    "se_domain": "google.com",
                    "location_code": 1012873,
                    "check_url": "https://www.google.com/search?q=plumber&...",
                    "items_count": 10,
                    "items": [
                        {
                            "type": "organic",
                            "rank_group": 1,
                            "rank_absolute": 1,
                            "domain": "yelp.com",
                            "title": "Top 10 Best Plumbers in Phoenix, AZ",
                            "url": "https://www.yelp.com/search?cflt=plumbing&find_loc=Phoenix",
                        },
                        {
                            "type": "organic",
                            "rank_group": 2,
                            "rank_absolute": 2,
                            "domain": "joesplumbing.com",
                            "title": "Joe's Plumbing - Phoenix AZ",
                            "url": "https://joesplumbing.com",
                        },
                    ],
                }
            ],
        }
    ],
    "tasks_count": 1,
    "tasks_error": 0,
}

ERROR_RESPONSE = {
    "version": "0.1",
    "status_code": 20000,
    "status_message": "Ok.",
    "tasks": [
        {
            "id": "task-err-001",
            "status_code": 40501,
            "status_message": "Invalid Field: location_code",
            "cost": 0,
            "result": None,
        }
    ],
    "tasks_count": 1,
    "tasks_error": 1,
}

SERVER_ERROR_BODY = {
    "version": "0.1",
    "status_code": 50000,
    "status_message": "Internal Server Error.",
}
