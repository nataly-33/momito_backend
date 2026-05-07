from io import BytesIO
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from .models import Quote, QuoteItem
from .serializers import QuoteSerializer


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.filter(deleted_at__isnull=True).select_related(
        'client', 'seller'
    ).prefetch_related('items__product')
    serializer_class = QuoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if hasattr(self.request.user, 'client_profile'):
            qs = qs.filter(client=self.request.user.client_profile)
        return qs

    def perform_create(self, serializer):
        seller = self.request.user
        serializer.save(seller=seller)

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf(self, request, pk=None):
        quote = self.get_object()
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('Title', parent=styles['Title'],
                                     fontSize=18, textColor=colors.HexColor('#1e3a5f'),
                                     alignment=TA_CENTER)
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'],
                                        fontSize=10, alignment=TA_CENTER)
        right_style = ParagraphStyle('Right', parent=styles['Normal'],
                                     fontSize=9, alignment=TA_RIGHT)

        story = []

        # Header
        story.append(Paragraph("TUMOMITO S.A.", title_style))
        story.append(Paragraph("Importadora Mayorista | ERP B2B", subtitle_style))
        story.append(Spacer(1, 0.5*cm))

        # Quote info
        info_data = [
            ['Cotización N°:', quote.numero_cotizacion, 'Fecha:', quote.created_at.strftime('%d/%m/%Y')],
            ['Cliente:', quote.client.company_name, 'Estado:', quote.get_status_display()],
            ['Ciudad:', quote.client.city or '-', 'Válida hasta:', str(quote.valid_until) if quote.valid_until else '-'],
        ]
        if quote.seller:
            info_data.append(['Vendedor:', f"{quote.seller.nombre} {quote.seller.apellido}", '', ''])

        info_table = Table(info_data, colWidths=[3*cm, 7*cm, 3*cm, 4*cm])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8edf5')),
            ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#e8edf5')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.5*cm))

        # Items table
        items_header = ['Código', 'Descripción', 'Cant.', 'Precio Unit.', 'Subtotal']
        items_data = [items_header]
        for item in quote.items.all():
            items_data.append([
                item.product.code or '-',
                item.product.nombre,
                str(item.quantity),
                f"Bs. {item.unit_price:.2f}",
                f"Bs. {item.subtotal:.2f}",
            ])
        items_data.append(['', '', '', 'TOTAL:', f"Bs. {quote.total:.2f}"])

        items_table = Table(items_data, colWidths=[2.5*cm, 8*cm, 2*cm, 3*cm, 3*cm])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
            ('FONTNAME', (3, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (3, -1), (-1, -1), 11),
            ('BACKGROUND', (3, -1), (-1, -1), colors.HexColor('#e8edf5')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f5f7fa')]),
        ]))
        story.append(items_table)

        if quote.notes:
            story.append(Spacer(1, 0.5*cm))
            story.append(Paragraph(f"<b>Notas:</b> {quote.notes}", styles['Normal']))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="cotizacion-{quote.numero_cotizacion}.pdf"'
        return response
