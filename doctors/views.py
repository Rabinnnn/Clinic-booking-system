from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import datetime

from appointments.services import get_available_slots
from appointments.serializers import AvailabilitySlotSerializer


class DoctorAvailabilityView(APIView):
    def get(self, request, id):
        date_str = request.query_params.get('date')
        if not date_str:
            return Response(
                {'error': 'Missing date parameter. Use ?date=YYYY-MM-DD'},
                status=400
            )
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=400
            )

        slots = get_available_slots(id, date)
        serializer = AvailabilitySlotSerializer(slots, many=True)
        return Response({'slots': serializer.data})