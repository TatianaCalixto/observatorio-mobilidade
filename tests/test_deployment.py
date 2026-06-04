"""Teste do deployment/schedule do pipeline (S07-T02)."""

from orchestration.deployment import CRON_DIARIO, NOME_DEPLOYMENT, criar_deployment


def test_deployment_tem_schedule_diario():
    deployment = criar_deployment()
    assert deployment.name == NOME_DEPLOYMENT
    assert deployment.flow_name == "observatorio-pipeline"
    assert deployment.schedules, "deployment deve ter um schedule"
    assert deployment.schedules[0].schedule.cron == CRON_DIARIO
