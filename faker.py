import sys
import networkx as nx

from PySide6.QtWidgets import QApplication, QWidget, QMainWindow, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem
from PySide6.QtWidgets import QScrollArea, QSizePolicy
from PySide6.QtSql import QSqlDatabase, QSqlQuery

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap

class DatabaseTables(QMainWindow):

    def __init__(self, parent=None):
        super(DatabaseTables, self).__init__(parent)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create a layout for the central widget
        self.layout = QHBoxLayout(central_widget)

        self.g = nx.DiGraph()

        db = QSqlDatabase.addDatabase("QPSQL")
        db.setHostName("localhost")
        db.setDatabaseName("pairing")
        db.setUserName("")
        db.setPassword("")
        ok = db.open()
        self.db = db

        if ok:
            self.find_nodes()    
            self.build_relations()
            self.display_graph()
        else:
            print("Failed to connect to database")
            sys.exit(1)


    def display_graph(self):
        A = nx.nx_agraph.to_agraph(self.g)

        A.layout(prog='dot')  # Use the 'dot' layout engine
        A.draw('graph.png')

        label = QLabel()
        pixmap = QPixmap('graph.png')
        label.setPixmap(pixmap)
        scroll_area = QScrollArea()
        scroll_area.setWidget(label)
        
        self.layout.addWidget(scroll_area)

    def build_relations(self):
        """Iterate through the nodes in the digraph in self.g and build the relations between them"""

        q = '''SELECT 
                kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
            JOIN 
                information_schema.key_column_usage AS kcu 
            ON 
                tc.constraint_name = kcu.constraint_name
            JOIN 
                information_schema.constraint_column_usage AS ccu 
            ON 
                ccu.constraint_name = tc.constraint_name
            WHERE 
                tc.table_name='{}' AND 
                tc.constraint_type = 'FOREIGN KEY';'''
        
        query = QSqlQuery()
        tables = []
        for node in self.g.nodes:
            tables.append(node)

        for node in tables:            
            query.exec(q.format(node))
            while query.next():  # Add this line
                record = query.record()
                #print(node , record.value('column_name'), " -> ", record.value('foreign_table_name'), ".", record.value('foreign_column_name'))
                self.g.add_edge(node, record.value('foreign_table_name'))

    def find_nodes(self):
        
        self.setLayout(self.layout)

        query = QSqlQuery("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        table = QTableWidget()
        table.setColumnCount(1)
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) 
        table.setHorizontalHeaderLabels(["List of Tables"])
        row = 0
        while query.next():
            if not (query.value(0).endswith('_aud') or query.value(0).endswith('_audit')):
                table.setRowCount(row + 1)
                table.setItem(row, 0, QTableWidgetItem(query.value(0)))
                self.g.add_node(query.value(0))
                row += 1
        self.layout.addWidget(table)
        
                            
if __name__ == '__main__':
    app = QApplication([])
    window = DatabaseTables()
    window.show()
    app.exec()