from locust import HttpUser, task, between

class TrendropUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_trends(self):
        # View trends sorted by velocity (most common action)
        self.client.get("/api/trends?sort=velocity")

    @task(2)
    def view_emerging_trends(self):
        # View emerging trends
        self.client.get("/api/trends/emerging")

    @task(1)
    def view_all_active_trends(self):
        # View all active trends
        self.client.get("/api/trends/all-active")

    @task(1)
    def get_health(self):
        # Hit the health endpoint
        self.client.get("/health")
