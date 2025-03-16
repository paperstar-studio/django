import inspect # for naming html templates the same as the function name, only to define it once ;0
import pandas as pd
from django.shortcuts import render


# Create your views here.
def mar_2025(request):
    df = pd.DataFrame([
        {'category':'exemplary graphs','title':'vienna complexity center','description/link':'d3 based visuals: https://csh.ac.at/visuals/'},
        {'category':'hygene','title':'hair curler','description/link':'https://olaplex.de/products/original-olaplex-n-10-bond-shaper-curl-defining-gel'},
        {'category':'recreation','title':'spain organic farms','description/link':'https://wwoof.es/en/'},
        {'category':'','title':'','description/link':''},
    ])
    return render( request, f"blog/{inspect.getframeinfo(inspect.currentframe()).function}.html", context={
        'table_data':df.to_html(classes=["table","table-sm","table-bordered", "table-striped"]),
    } )






#
