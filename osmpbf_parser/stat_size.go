package main

import (
    "fmt"
    "os"
    "path/filepath"

    "github.com/qedus/osmpbf"
)

func getPBFStats(pbfFile string) error {
    file, err := os.Open(pbfFile)
    if err != nil {
        return err
    }
    defer file.Close()

    fileInfo, err := file.Stat()
    if err != nil {
        return err
    }
    fileSize := fileInfo.Size()

    decoder := osmpbf.NewDecoder(file)
    if err := decoder.Start(4); err != nil {
        return err
    }

    var nodes, ways, relations int

    for {
        v, err := decoder.Decode()
        if err != nil {
            break
        }

        switch v.(type) {
        case *osmpbf.Node:
            nodes++
        case *osmpbf.Way:
            ways++
        case *osmpbf.Relation:
            relations++
        }
    }

    fmt.Printf("=== СТАТИСТИКА ФАЙЛА: %s ===\n", filepath.Base(pbfFile))
    fmt.Printf("Размер файла: %.2f MB\n", float64(fileSize)/(1024*1024))
    fmt.Printf("Узлов (nodes): %d\n", nodes)
    fmt.Printf("Путей (ways): %d\n", ways)
    fmt.Printf("Отношений (relations): %d\n", relations)
    fmt.Printf("Всего объектов: %d\n", nodes+ways+relations)

    return nil
}

func main() {
    if len(os.Args) < 2 {
        fmt.Println("Использование: go run main.go <file.osm.pbf>")
        return
    }

    if err := getPBFStats(os.Args[1]); err != nil {
        fmt.Printf("Ошибка: %v\n", err)
    }
}