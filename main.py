from flask import Flask, render_template, request


app = Flask(__name__)

@app.route("/")
def Menu():
    return render_template("Menu.html")

if __name__ == "__main__":
    app.run()