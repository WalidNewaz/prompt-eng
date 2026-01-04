from src.runtime.workflows import IncidentPlan

class FakePlanGenerator:
    def __init__(self, plan: IncidentPlan):
        self.plan = plan

    async def generate(self, **kwargs) -> IncidentPlan:
        return self.plan
