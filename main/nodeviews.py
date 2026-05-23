#import the necessary modules
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from dashboard.models import Node, Connection
#import Q for complex queries
from django.db.models import Q
def lastnodeid(request):
    last_node = Node.objects.last()
    last_id = last_node.id if last_node else 0
    return JsonResponse({'last_id': last_id+1})
def get_board_data(request):
    # Load only title nodes
    title_nodes = Node.objects.filter(type='title')
    title_ids = title_nodes.values_list('id', flat=True)

    # Load only connections between title nodes
    connections = Connection.objects.filter(
        source_id__in=title_ids,
        target_id__in=title_ids
    )

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
            for n in title_nodes
        ],
        "connections": [
            {
                "id": c.id,
                "source": c.source_id,
                "target": c.target_id,
                "label": c.label or "",
                "color": c.color or ""
            }
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
    node_id = request.GET.get('id')
    if not node_id:
        return JsonResponse({"error": "Missing id"}, status=400)

    node = Node.objects.get(id=node_id)

    # outgoing connections
    connections = Connection.objects.filter(Q(source=node) | Q(target=node))

    # collect connected nodes that are not already sent
    connected_nodes = []
    for c in connections:
        # add source if it’s not the clicked node
        if c.source.id != node.id:
            connected_nodes.append({
                "id": c.source.id,
                "title": c.source.title,
                "description": c.source.description,
                "x": c.source.x,
                "y": c.source.y,
                "type": c.source.type,
                "imglink": c.source.imglink,
                "videolink": c.source.videolink,
                "ytlink": c.source.ytlink,
                "image": c.source.image.url if c.source.image else None
            })
        # add target if it’s not the clicked node
        if c.target.id != node.id:
            connected_nodes.append({
                "id": c.target.id,
                "title": c.target.title,
                "description": c.target.description,
                "x": c.target.x,
                "y": c.target.y,
                "type": c.target.type,
                "imglink": c.target.imglink,
                "videolink": c.target.videolink,
                "ytlink": c.target.ytlink,
                "image": c.target.image.url if c.target.image else None
            })
    return JsonResponse({
        "id": node.id,
        "title": node.title,
        "description": node.description,
        "imglink": node.imglink,
        "videolink": node.videolink,
        "ytlink": node.ytlink,
        "image": node.image.url if node.image else None,
        "connections": [
            {
                "id": c.id,
                "source_id": c.source.id,
                "source_title": c.source.title,
                "target_id": c.target.id,
                "target_title": c.target.title,
                "label": c.label or "",
                "color": c.color or ""
            } for c in connections
        ],
        "connected_nodes": connected_nodes
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


def get_connected_nodes(request):
    node_id = request.GET.get('id')
    # all connections from this node
    connections = Connection.objects.filter(source_id=node_id)
    nodes = Node.objects.filter(id__in=connections.values_list('target_id', flat=True))

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
            {"source": c.source_id, "target": c.target_id, "label": c.label or "", "color": c.color or ""}
            for c in connections
        ]
    })
