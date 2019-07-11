from django.utils import numberformat


class NumberUtil(object):

    @staticmethod
    def format_score(score):
        return numberformat.format(score, decimal_sep='', decimal_pos=0, grouping=3, thousand_sep='.', force_grouping=True)
