from django.db import models

class BillSummaryCache(models.Model):
    bill_id = models.CharField(max_length=50, unique=True, verbose_name="의안번호")
    summary_text = models.TextField(verbose_name="3줄 요약")
    tag1 = models.CharField(max_length=50, null=True, blank=True, verbose_name="태그1")
    tag2 = models.CharField(max_length=50, null=True, blank=True, verbose_name="태그2")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일시")

    def __str__(self):
        return f"[{self.bill_id}] 요약 데이터"