import operator

from feat.agents.application import feat
from feat.common.text_helper import format_block
from feat.database import view


@feat.register_view
class Join(view.JavascriptView):

    design_doc_id = 'featjs'
    name = 'join'

    map = format_block('''
    function(doc) {
        if (doc.linked) {
            for (var x = 0; x < doc.linked.length; x++) {
                var row = doc.linked[x];

                // emit link from document to linkee
                if (row[3]) {
                    for (var xx=0; xx < row[3].length; xx ++) {
                        emit([doc["_id"], row[3][xx]], {"_id": row[1]});
                    }
                };
                emit([doc["_id"], row[0]], {"_id": row[1]});

                // emit reverse link, from linkee to linker
                if (row[2]) {
                    for (var xx=0; xx < row[2].length; xx ++) {
                        emit([row[1], row[2][xx]], null);
                    }
                };
                emit([row[1], doc[".type"]], null);
            }
        }
    }''')

    @staticmethod
    def perform_map(doc):
        if 'linked' in doc:
            doc_id = doc['_id']
            for row in doc['linked']:
                if row[3]:
                    for role in row[3]:
                        yield (doc_id, role), {'_id': row[1]}
                yield (doc_id, row[0]), {'_id': row[1]}

                if row[2]:
                    for role in row[2]:
                        yield (row[1], role), None
                yield (row[1], doc['.type']), None

    @staticmethod
    def keys(doc_id, type_name=None):
        if type_name is not None:
            return dict(key=(doc_id, type_name))
        else:
            return dict(startkey=(doc_id, ), endkey=(doc_id, {}))


def fetch(connection, doc_id, type_name=None):
    keys = Join.keys(doc_id, type_name)
    return connection.query_view(Join, include_docs=True, **keys)


def get_ids(connection, doc_id, type_name=None):
    keys = Join.keys(doc_id, type_name)
    d = connection.query_view(Join, parse_results=False, **keys)
    d.addCallback(operator.itemgetter(2))
    return d