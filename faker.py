import sys
import networkx as nx

from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QLineEdit, QVBoxLayout, QTableWidget, QTableWidgetItem
from PySide6.QtWidgets import QScrollArea, QSizePolicy, QSplitter, QPushButton, QMessageBox
from PySide6.QtSql import QSqlDatabase, QSqlQuery

from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap

class DatabaseDialog(QDialog):
    def __init__(self, parent=None):
        super(DatabaseDialog, self).__init__(parent)

        self.layout = QVBoxLayout(self)

        self.host_label = QLabel("Host:")
        self.host_field = QLineEdit()
        self.layout.addWidget(self.host_label)
        self.layout.addWidget(self.host_field)

        self.database_label = QLabel("Database:")
        self.database_field = QLineEdit()
        self.layout.addWidget(self.database_label)
        self.layout.addWidget(self.database_field)

        self.username_label = QLabel("Username:")
        self.username_field = QLineEdit()
        self.layout.addWidget(self.username_label)
        self.layout.addWidget(self.username_field)

        self.password_label = QLabel("Password:")
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.Password)
        self.layout.addWidget(self.password_label)
        self.layout.addWidget(self.password_field)

        self.button = QPushButton("Connect")
        self.button.clicked.connect(self.connect_to_database)
        self.layout.addWidget(self.button)

    def connect_to_database(self):
        db = QSqlDatabase.addDatabase("QPSQL")
        db.setHostName(self.host_field.text())
        db.setDatabaseName(self.database_field.text())
        db.setUserName(self.username_field.text())
        db.setPassword(self.password_field.text())
        ok = db.open()

        if ok:
            self.db = db
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Could not connect to the database")


class DatabaseTables(QMainWindow):

    def __init__(self, parent=None):
        super(DatabaseTables, self).__init__(parent)
        
        self.central_widget = QSplitter()
        self.central_widget.setSizes([100, 400])
        self.setCentralWidget(self.central_widget)

        # we are going to create two graphs, the first graph will contain all the 
        # foreign keys and the second graph will not contain self referential keys
        # that is needed because topological sort works only on Directed Acyclic Graphs
        # graphs with self referential keys are not DAGs

        self.g = nx.DiGraph()
        self.dag = nx.DiGraph()

        self.find_nodes()    
        self.build_relations()
        try:

            self.g = nx.DiGraph()
            for cycle in nx.simple_cycles(self.dag):
                # Convert the cycle to a list of edges
                edges = [(cycle[i], cycle[i + 1]) for i in range(len(cycle) - 1)]
                # Add the last edge to close the cycle
                edges.append((cycle[-1], cycle[0]))
                # Add the edges to the graph
                self.g.add_edges_from(edges)
            
        except nx.exception.NetworkXNoCycle:
            print("No cycles found in the graph")
        self.display_graph(self.g)



    def display_graph(self, graph):
        a = nx.nx_agraph.to_agraph(graph)

        a.layout(prog='sfdp')  # Use the 'dot' layout engine
        a.draw('graph.png')

        label = QLabel()
        pixmap = QPixmap('graph.png')
        label.setPixmap(pixmap)
        scroll_area = QScrollArea()
        scroll_area.setWidget(label)
        
        self.central_widget.addWidget(scroll_area)

    def build_relations(self):
        """Iterate through the nodes in the digraph in self.g and build the relations between them"""

        query = QSqlQuery()

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
        
        
        tables = []
        for node in self.g.nodes:
            tables.append(node)

        for node in tables:            
            query.exec(q.format(node))
            while query.next():  # Add this line
                record = query.record()
                self.g.add_edge(node, record.value('foreign_table_name'))
                if node != record.value('foreign_table_name'):
                    self.dag.add_edge(node, record.value('foreign_table_name'))

#        for node in nx.topological_sort(self.dag):
#            print(node)


    def find_nodes(self):
        """Find all the tables in the database and add them to the graph"""
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
                self.dag.add_node(query.value(0))
                row += 1
        self.central_widget.addWidget(table)
        
                            
if __name__ == '__main__':
    app = QApplication([])
    dialog = DatabaseDialog()

    if dialog.exec_() == QDialog.Accepted:
        window = DatabaseTables()
        window.db = dialog.db
        window.show()
        app.exec()
        pass
    else:
        # Quit the application
        app.quit()
        
