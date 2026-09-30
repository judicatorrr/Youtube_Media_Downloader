from PySide6.QtWidgets import QProxyStyle, QStyle, QStyleFactory

class DelayedTooltipStyle(QProxyStyle):
    def __init__(self):
        super().__init__(QStyleFactory.create("Fusion"))

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.SH_ToolTip_WakeUpDelay:
            return 2500
        if hint == QStyle.SH_ToolTip_FallAsleepDelay:
            return 0
        return super().styleHint(hint, option, widget, returnData)
