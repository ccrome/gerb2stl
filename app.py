import dash
from dash import dcc, html, Input, Output, State
import flask
import base64
import tempfile
import os
import uuid
from converter import svg_to_stl, gerber_to_svg
import logging

logging.basicConfig(level=logging.INFO)

# Flask + Dash setup
server = flask.Flask(__name__)
app = dash.Dash(__name__, server=server)

# Token -> STL file path mapping
token_file_map = {}

app.layout = html.Div([
    html.H1("Gerber to STL Converter"),
    dcc.Upload(
        id='upload-gerber',
        children=html.Div(['Drag & Drop or ', html.A('Select a Gerber File')]),
        style={
            'width': '50%',
            'height': '100px',
            'lineHeight': '100px',
            'borderWidth': '2px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': 'auto'
        },
        multiple=False
    ),
    html.Div(id='upload-status', style={'textAlign': 'center', 'marginTop': 20}),
    html.Div(id='download-link', style={'textAlign': 'center', 'marginTop': 20})
])


@app.callback(
    Output('upload-status', 'children'),
    Output('download-link', 'children'),
    Input('upload-gerber', 'contents'),
    State('upload-gerber', 'filename'),
)
def handle_upload(contents, filename):
    if contents is None:
        return "", ""

    logging.info(f"Received file: {filename}")

    content_type, content_string = contents.split(',')
    file_data = base64.b64decode(content_string)

    tmpdir = tempfile.mkdtemp()
    input_path = os.path.join(tmpdir, filename)
    with open(input_path, 'wb') as f:
        f.write(file_data)
    logging.info(f"Wrote uploaded file to {input_path}")

    stl_path = os.path.join(tmpdir, f"{input_path}.stl")
    try:
        svg_path = f"{input_path}.svg"
        logging.info(f"converting {input_path} to {svg_path}")
        gerber_to_svg(input_path, svg_path)
        logging.info(f"converting {svg_path} to {stl_path}")
        svg_to_stl(svg_path, stl_path)
        logging.info(f"Generated STL at {stl_path}")
    except Exception as e:
        logging.exception("Conversion failed")
        return f"Conversion failed: {e}", ""

    # Register file with a unique token
    token = str(uuid.uuid4())
    token_file_map[token] = {"stl_path": stl_path, "stl_name": f"{filename}.stl"}
    download_url = f"/download/{token}"

    return "Conversion successful!", html.A("Download STL", href=download_url, target="_blank")


@server.route("/download/<token>")
def serve_stl(token):
    stl_path = token_file_map.get(token)['stl_path']
    name = token_file_map.get(token)['stl_name']
    print(token_file_map)
    if not stl_path:
        logging.warning(f"Download requested with unknown token: {token}")
        return "Invalid or expired download token", 404

    if not os.path.exists(stl_path):
        logging.error(f"STL file path for token {token} does not exist: {stl_path}")
        return "STL file not found", 404

    logging.info(f"Serving STL file for token {token}: {stl_path}")
    return flask.send_file(stl_path, as_attachment=True, download_name=name)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
