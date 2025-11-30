#import the necessary modules
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from dashboard.models import Node, Connection

def lastnodeid(request):
    last_node = Node.objects.last()
    last_id = last_node.id if last_node else 0
    return JsonResponse({'last_id': last_id+1})
def get_board_data(request):
    nodes = Node.objects.all()#filter(type='title')
    connections = Connection.objects.all()
    print('>> connections', connections)
    return JsonResponse({
        "nodes": [
            {
                "id": n.id,
                "title": n.title,
                "description": n.description,
                "x": n.x,
                "y": n.y,
                "type": n.type,
                "imglink": n.imglink,
                "videolink": n.videolink,
                "ytlink": n.ytlink,
                "image": n.image.url if n.image else None
            }
            for n in nodes
        ],
        "connections": [
            {"id": c.id, "source": c.source_id, "target": c.target_id, "label": c.label or "", "color": c.color or ""}
            for c in connections
        ]
    })
@csrf_exempt
def create_node(request):
    if request.method == "POST":
        title = request.POST.get("title", "Untitled")
        description = request.POST.get("description", "")
        x = request.POST.get("x", 100)
        y = request.POST.get("y", 100)
        imglink = request.POST.get("imglink", '')
        videolink = request.POST.get("videolink", '')
        ytlink = request.POST.get("ytlink", '')
        type_ = request.POST.get("type", "note")
        image = request.FILES.get("image")
        node = Node.objects.create(
            title=title,
            description=description,
            imglink=imglink,
            videolink=videolink,
            ytlink=ytlink,
            x=x,
            y=y,
            type=type_,
            image=image if image else None
        )

        return JsonResponse({
            "id": node.id,
            "title": node.title,
            "description": node.description,
            "imglink": node.imglink,
            "videolink": node.videolink,
            "ytlink": node.ytlink,
            "x": node.x,
            "y": node.y,
            "type": node.type,
            "image": node.image.url if node.image else None
        })
@csrf_exempt
def update_node_position(request, node_id):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        try:
            node = Node.objects.get(id=node_id)
            node.x = data.get("x", node.x)
            node.y = data.get("y", node.y)
            node.save()
            return JsonResponse({"status": "ok"})
        except Node.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Node not found"}, status=404)
@csrf_exempt
def create_connection(request):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        source_id = data.get("source")
        target_id = data.get("target")
        label = data.get("label", "")
        try:
            source = Node.objects.get(id=source_id)
            target = Node.objects.get(id=target_id)
            conn, created = Connection.objects.update_or_create(
                source=source,
                target=target,
                color='white',
                defaults={"label": label}
            )
            return JsonResponse({"status": "ok", "id": conn.id})
        except Node.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Node not found"}, status=404)

@csrf_exempt
def updatenode(request):
    id=request.POST.get('iddata')
    title=request.POST.get('titledata')
    desc=request.POST.get('descdata')
    imglink=request.POST.get('imglinkdata')
    videolink=request.POST.get('videolinkdata')
    ytlink=request.POST.get('ytlinkdata')
    img=request.FILES.get('imgdata')
    print('>> ids, img', id, img, request.POST)
    node=Node.objects.get(id=id)
    node.title=title
    node.imglink=imglink
    node.videolink=videolink
    node.ytlink=ytlink
    node.description=desc
    if img:
        node.image=img
    node.save()

    return JsonResponse({
        'success':True
    })
@csrf_exempt
def save_board(request):
    if request.method == "POST":
        nodes_data = json.loads(request.POST.get("nodes", "[]"))
        connections_data = json.loads(request.POST.get("connections", "[]"))

        node_map = {}
        for idx, n in enumerate(nodes_data):
            node, created = Node.objects.update_or_create(
                id=n.get("id"),
                defaults={
                    "title": n.get("title", "Untitled"),
                    "description": n.get("description", ""),
                    "x": n.get("x", 100),
                    "y": n.get("y", 100),
                    "type": n.get("type", "note"),
                }
            )
            image = request.FILES.get(f"image_{idx}")
            if image:
                node.image = image
                node.save()

            node_map[n["id"]] = node

        # Save connections
        for c in connections_data:
            try:
                Connection.objects.update_or_create(
                    source=node_map[c["source"]],
                    target=node_map[c["target"]],
                    defaults={"label": c.get("label", "")}
                )
            except KeyError:
                continue  # if node mapping fails, skip

        return JsonResponse({"status": "ok"})

@csrf_exempt
def update_connection(request, conn_id):
    if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        try:
            conn = Connection.objects.get(id=conn_id)
            conn.label = data.get("label", "")
            conn.save()
            return JsonResponse({"status": "ok"})
        except Connection.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Connection not found"}, status=404)

def getnodedata(request):
    id=request.GET.get('id')
    node=Node.objects.get(id=id)
    return JsonResponse({
        'id': node.id,
        'title': node.title,
        'description': node.description,
        'x': node.x,
        'y': node.y,
        'type': node.type,
        'imglink': node.imglink,
        'videolink': node.videolink,
        'ytlink': node.ytlink,
        'image': node.image.url if node.image else None,
        'connections': [
            {
                'id': c.id,
                'source': Node.objects.get(id=c.source_id).title,
                'target': Node.objects.get(id=c.target_id).title,
                'source_id': c.source_id,
                'target_id': c.target_id,
                'label': c.label,
            }
            for c in Connection.objects.filter(source=node) | Connection.objects.filter(target=node)
        ],
    })
def updatelabel(request):
    id=request.GET.get('id')
    label=request.GET.get('label').lower()
    conn=Connection.objects.get(id=id)
    conn.label=label
    if label=='against':
        conn.color='red'
    elif label=='support':
        conn.color='green'
    elif label=='neutral':
        conn.color='yellow'
    elif label=='funds':
        conn.color='blue'
    else:
        conn.color='white'
    conn.save()
    return JsonResponse({
        'success':True
    })
