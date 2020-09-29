from connexion.resolver import RestyResolver
import connexion

if __name__ == '__main__':
    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('nvidiaclarasegmentation.yaml', resolver=RestyResolver('api'))
    app.add_api('finetune.yaml', resolver=RestyResolver('api'))
    app.run(port=9090)

