from notificaciones.checks.context import CheckContext

class BaseAnalyzer:
    def __init__(self, check_classes):
        self.check_classes = check_classes

    def analyze(self, ctx: CheckContext, movimiento):
        alertas = []
        for CheckClass in self.check_classes:
            check_instance = CheckClass(ctx, movimiento)
            if check_instance.is_enabled():
                alerta = check_instance.run()
                if alerta:
                    alertas.append(alerta)
        return alertas
