package main

import (
	"encoding/csv"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/qedus/osmpbf"
	"golang.org/x/text/encoding/charmap"
)

type OSMData struct {
	Nodes     []Node
	Ways      []Way
	Relations []Relation
}

type Node struct {
	ID   int64
	Lat  float64
	Lon  float64
	Tags map[string]string
}

type Way struct {
	ID      int64
	NodeIDs []int64
	Tags    map[string]string
}

type Relation struct {
	ID      int64
	Members []Member
	Tags    map[string]string
}

type Member struct {
	Type string
	Ref  int64
	Role string
}

type OSMToCSVConverter struct {
	OutputDir string
	Data      OSMData
}

func NewOSMToCSVConverter(outputDir string) *OSMToCSVConverter {
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		log.Fatal("Ошибка создания директории:", err)
	}

	return &OSMToCSVConverter{
		OutputDir: outputDir,
		Data: OSMData{
			Nodes:     make([]Node, 0),
			Ways:      make([]Way, 0),
			Relations: make([]Relation, 0),
		},
	}
}

func (c *OSMToCSVConverter) Convert(pbfFile string) error {
	startTime := time.Now()
	fmt.Printf("Конвертация %s в CSV...\n", pbfFile)
	fmt.Printf("Выходная директория: %s\n", c.OutputDir)

	file, err := os.Open(pbfFile)
	if err != nil {
		return fmt.Errorf("ошибка открытия файла: %v", err)
	}
	defer file.Close()

	decoder := osmpbf.NewDecoder(file)

	decoder.SetBufferSize(osmpbf.MaxBlobSize)

	if err := decoder.Start(4); err != nil {
		return fmt.Errorf("ошибка инициализации декодера: %v", err)
	}

	var nodeCount, wayCount, relationCount int

	for {
		if v, err := decoder.Decode(); err != nil {
			break
		} else {
			switch v := v.(type) {
			case *osmpbf.Node:
				c.processNode(v)
				nodeCount++
				if nodeCount%100000 == 0 {
					fmt.Printf("Обработано узлов: %d\n", nodeCount)
				}

			case *osmpbf.Way:
				c.processWay(v)
				wayCount++
				if wayCount%10000 == 0 {
					fmt.Printf("Обработано путей: %d\n", wayCount)
				}

			case *osmpbf.Relation:
				c.processRelation(v)
				relationCount++
				if relationCount%1000 == 0 {
					fmt.Printf("Обработано отношений: %d\n", relationCount)
				}
			}
		}
	}

	c.saveToCSV()

	processingTime := time.Since(startTime).Seconds()

	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Println("КОНВЕРТАЦИЯ ЗАВЕРШЕНА")
	fmt.Println(strings.Repeat("=", 50))
	fmt.Printf("Обработано файлов: 1\n")
	fmt.Printf("Найдено узлов: %d\n", len(c.Data.Nodes))
	fmt.Printf("Найдено путей: %d\n", len(c.Data.Ways))
	fmt.Printf("Найдено отношений: %d\n", len(c.Data.Relations))
	fmt.Printf("Время обработки: %.2f секунд\n", processingTime)
	fmt.Printf("CSV файлы сохранены в: %s\n", c.OutputDir)

	return nil
}

func (c *OSMToCSVConverter) processNode(n *osmpbf.Node) {
	node := Node{
		ID:   n.ID,
		Lat:  n.Lat,
		Lon:  n.Lon,
		Tags: make(map[string]string),
	}

	for k, v := range n.Tags {
		node.Tags[k] = v
	}

	c.Data.Nodes = append(c.Data.Nodes, node)
}

func (c *OSMToCSVConverter) processWay(w *osmpbf.Way) {
	way := Way{
		ID:      w.ID,
		NodeIDs: make([]int64, len(w.NodeIDs)),
		Tags:    make(map[string]string),
	}

	copy(way.NodeIDs, w.NodeIDs)

	for k, v := range w.Tags {
		way.Tags[k] = v
	}

	c.Data.Ways = append(c.Data.Ways, way)
}

func (c *OSMToCSVConverter) processRelation(r *osmpbf.Relation) {
	relation := Relation{
		ID:      r.ID,
		Members: make([]Member, len(r.Members)),
		Tags:    make(map[string]string),
	}

	for i, m := range r.Members {
		var memberType string
		switch m.Type {
		case osmpbf.NodeType:
			memberType = "n"
		case osmpbf.WayType:
			memberType = "w"
		case osmpbf.RelationType:
			memberType = "r"
		}

		relation.Members[i] = Member{
			Type: memberType,
			Ref:  m.ID,
			Role: m.Role,
		}
	}

	for k, v := range r.Tags {
		relation.Tags[k] = v
	}

	c.Data.Relations = append(c.Data.Relations, relation)
}

func (c *OSMToCSVConverter) saveToCSV() {
	fmt.Println("Сохранение данных в CSV...")

	if len(c.Data.Nodes) > 0 {
		c.saveNodesCSV()
	}

	if len(c.Data.Ways) > 0 {
		c.saveWaysCSV()
	}

	if len(c.Data.Relations) > 0 {
		c.saveRelationsCSV()
	}

	c.saveTagsCSV()
}

func (c *OSMToCSVConverter) saveNodesCSV() {
	filename := filepath.Join(c.OutputDir, "nodes.csv")
	file, err := os.Create(filename)
	if err != nil {
		log.Fatal("Ошибка создания файла nodes.csv:", err)
	}
	defer file.Close()

	writer := csv.NewWriter(charmap.Windows1251.NewEncoder().Writer(file))
	defer writer.Flush()

	headers := []string{"id", "latitude", "longitude"}
	if err := writer.Write(headers); err != nil {
		log.Fatal("Ошибка записи заголовка nodes.csv:", err)
	}

	for _, node := range c.Data.Nodes {
		record := []string{
			strconv.FormatInt(node.ID, 10),
			strconv.FormatFloat(node.Lat, 'f', 7, 64),
			strconv.FormatFloat(node.Lon, 'f', 7, 64),
		}
		if err := writer.Write(record); err != nil {
			log.Fatal("Ошибка записи данных nodes.csv:", err)
		}
	}

	fmt.Printf("Узлы сохранены в: %s (%d записей)\n", filename, len(c.Data.Nodes))
}

func (c *OSMToCSVConverter) saveWaysCSV() {
	filename := filepath.Join(c.OutputDir, "ways.csv")
	file, err := os.Create(filename)
	if err != nil {
		log.Fatal("Ошибка создания файла ways.csv:", err)
	}
	defer file.Close()

	writer := csv.NewWriter(charmap.Windows1251.NewEncoder().Writer(file))
	defer writer.Flush()

	headers := []string{"id", "node_ids", "nodes_count"}
	if err := writer.Write(headers); err != nil {
		log.Fatal("Ошибка записи заголовка ways.csv:", err)
	}

	for _, way := range c.Data.Ways {
		nodeIDs := make([]string, len(way.NodeIDs))
		for i, id := range way.NodeIDs {
			nodeIDs[i] = strconv.FormatInt(id, 10)
		}

		record := []string{
			strconv.FormatInt(way.ID, 10),
			strings.Join(nodeIDs, ";"),
			strconv.Itoa(len(way.NodeIDs)),
		}
		if err := writer.Write(record); err != nil {
			log.Fatal("Ошибка записи данных ways.csv:", err)
		}
	}

	fmt.Printf("Пути сохранены в: %s (%d записей)\n", filename, len(c.Data.Ways))
}

func (c *OSMToCSVConverter) saveRelationsCSV() {
	filename := filepath.Join(c.OutputDir, "relations.csv")
	file, err := os.Create(filename)
	if err != nil {
		log.Fatal("Ошибка создания файла relations.csv:", err)
	}
	defer file.Close()

	writer := csv.NewWriter(charmap.Windows1251.NewEncoder().Writer(file))
	defer writer.Flush()

	headers := []string{"id", "members", "members_count"}
	if err := writer.Write(headers); err != nil {
		log.Fatal("Ошибка записи заголовка relations.csv:", err)
	}

	for _, relation := range c.Data.Relations {
		members := make([]string, len(relation.Members))
		for i, member := range relation.Members {
			members[i] = fmt.Sprintf("%s%d:%s", member.Type, member.Ref, member.Role)
		}

		record := []string{
			strconv.FormatInt(relation.ID, 10),
			strings.Join(members, ";"),
			strconv.Itoa(len(relation.Members)),
		}
		if err := writer.Write(record); err != nil {
			log.Fatal("Ошибка записи данных relations.csv:", err)
		}
	}

	fmt.Printf("Отношения сохранены в: %s (%d записей)\n", filename, len(c.Data.Relations))
}

func (c *OSMToCSVConverter) saveTagsCSV() {
	if len(c.Data.Nodes) > 0 {
		c.saveEntityTags("nodes_tags.csv", c.Data.Nodes, "node_id")
	}

	if len(c.Data.Ways) > 0 {
		c.saveEntityTags("ways_tags.csv", c.Data.Ways, "way_id")
	}

	if len(c.Data.Relations) > 0 {
		c.saveEntityTags("relations_tags.csv", c.Data.Relations, "relation_id")
	}
}

func (c *OSMToCSVConverter) saveEntityTags(filename string, entities interface{}, idFieldName string) {
	var allTags []struct {
		ID    int64
		Key   string
		Value string
	}

	switch e := entities.(type) {
	case []Node:
		for _, entity := range e {
			for key, value := range entity.Tags {
				if value != "" {
					allTags = append(allTags, struct {
						ID    int64
						Key   string
						Value string
					}{entity.ID, key, value})
				}
			}
		}
	case []Way:
		for _, entity := range e {
			for key, value := range entity.Tags {
				if value != "" {
					allTags = append(allTags, struct {
						ID    int64
						Key   string
						Value string
					}{entity.ID, key, value})
				}
			}
		}
	case []Relation:
		for _, entity := range e {
			for key, value := range entity.Tags {
				if value != "" {
					allTags = append(allTags, struct {
						ID    int64
						Key   string
						Value string
					}{entity.ID, key, value})
				}
			}
		}
	}

	if len(allTags) == 0 {
		return
	}

	filename = filepath.Join(c.OutputDir, filename)
	file, err := os.Create(filename)
	if err != nil {
		log.Fatal("Ошибка создания файла тегов:", err)
	}
	defer file.Close()

	writer := csv.NewWriter(charmap.Windows1251.NewEncoder().Writer(file))
	defer writer.Flush()

	headers := []string{idFieldName, "key", "value"}
	if err := writer.Write(headers); err != nil {
		log.Fatal("Ошибка записи заголовка тегов:", err)
	}

	for _, tag := range allTags {
		record := []string{
			strconv.FormatInt(tag.ID, 10),
			tag.Key,
			tag.Value,
		}
		if err := writer.Write(record); err != nil {
			log.Fatal("Ошибка записи данных тегов:", err)
		}
	}

	entityType := strings.Split(filename, "_")[0]
	entityType = filepath.Base(entityType)
	fmt.Printf("Теги %s сохранены в: %s (%d записей)\n", entityType, filename, len(allTags))
}

func createReadme(outputDir string) {
	readmeContent := `# OSM CSV Export

Файлы в этой директории содержат данные из OSM PBF файла в CSV формате.

## Описание файлов:

1. **nodes.csv** - Узлы (точки)
   - id: ID узла
   - latitude: Широта
   - longitude: Долгота

2. **ways.csv** - Пути (линии, полигоны)
   - id: ID пути
   - node_ids: Список ID узлов через ';'
   - nodes_count: Количество узлов

3. **relations.csv** - Отношения (группы объектов)
   - id: ID отношения
   - members: Список членов в формате 'типID:роль'
   - members_count: Количество членов

4. **nodes_tags.csv** - Теги узлов
   - node_id: ID узла
   - key: Ключ тега
   - value: Значение тега

5. **ways_tags.csv** - Теги путей
   - way_id: ID пути
   - key: Ключ тега
   - value: Значение тега

6. **relations_tags.csv** - Теги отношений
   - relation_id: ID отношения
   - key: Ключ тега
   - value: Значение тега

## Примечания:
- Все ID уникальны в пределах своего типа
- Координаты в WGS84 (стандартные GPS координаты)
- Пустые поля обозначены пустыми строками
`

	filename := filepath.Join(outputDir, "README.txt")
	if err := os.WriteFile(filename, []byte(readmeContent), 0644); err != nil {
		log.Fatal("Ошибка создания README:", err)
	}
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Использование: go run main.go <input.osm.pbf> [output_directory]")
		fmt.Println("Пример: go run main.go data.osm.pbf my_csv_output")
		os.Exit(1)
	}

	inputFile := os.Args[1]
	var outputDir string
	if len(os.Args) > 2 {
		outputDir = os.Args[2]
	} else {
		baseName := filepath.Base(inputFile)
		ext := filepath.Ext(baseName)
		outputDir = strings.TrimSuffix(baseName, ext) + "_csv"
	}

	if _, err := os.Stat(inputFile); os.IsNotExist(err) {
		fmt.Printf("Ошибка: файл %s не найден\n", inputFile)
		os.Exit(1)
	}

	converter := NewOSMToCSVConverter(outputDir)
	if err := converter.Convert(inputFile); err != nil {
		fmt.Printf("Критическая ошибка: %v\n", err)
		os.Exit(1)
	}

	createReadme(outputDir)
	fmt.Println("\nСоздан README.txt с описанием файлов")
}
