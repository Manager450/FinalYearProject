class DecimalConverter:
    regex = r'\d+(\.\d{1,2})?'

    def to_python(self, value):
        return float(value)
    
    def to_url(self, value):
        return str(value)