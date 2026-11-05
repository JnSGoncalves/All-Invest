from fastapi import APIRouter, Depends, Query, Response

from ..dependencies.auth import CurrentUser, get_current_user
from ..dependencies.components import get_report_service
from ..interfaces import IReportService

router = APIRouter(
    prefix="/api/reports",
    tags=["reports"],
    dependencies=[Depends(get_current_user)],
)

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get(
    "/export",
    response_class=Response,
    responses={
        200: {"content": {XLSX_MEDIA_TYPE: {}}, "description": "Planilha Excel da carteira."},
        401: {"description": "Autenticação ou chave de API inválida."},
        404: {"description": "Carteira inexistente ou pertencente a outro usuário."},
    },
)
async def exportar_planilha(
    current_user: CurrentUser,
    portfolio_id: int | None = Query(None, gt=0, description="Restringe a uma carteira."),
    reports: IReportService = Depends(get_report_service),
):
    """Planilha com Resumo, Posições e uma aba por ação, separada para cada ativo."""
    content = await reports.export_workbook(current_user.user_id, portfolio_id)
    return Response(
        content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="all-invest-carteira.xlsx"'},
    )
