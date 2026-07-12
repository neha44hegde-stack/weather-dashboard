class FloatConverter:
    """URL path converter for signed floats, e.g. -122.4194 or 37.7749."""

    regex = r"-?\d+(?:\.\d+)?"

    def to_python(self, value):
        return float(value)

    def to_url(self, value):
        return str(value)
