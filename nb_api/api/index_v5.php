<?php
// Define allowed origins
$allowed_origins = array(
    "http://localhost:3000",
    "http://localhost:8501",
    "https://haiku.ainewsbrew.com",
    "https://ainewsbrew.com",
    "https://www.ainewsbrew.com"
);

// Check if the origin is allowed and set the appropriate header
if (isset($_SERVER['HTTP_ORIGIN'])) {
    $origin = $_SERVER['HTTP_ORIGIN'];
    if (in_array($origin, $allowed_origins)) {
        header("Access-Control-Allow-Origin: $origin");
        header('Access-Control-Allow-Credentials: true');
        header('Access-Control-Max-Age: 86400');    // cache for 1 day
    }
}

// Access-Control headers are received during OPTIONS requests
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    if (isset($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_METHOD']))
        header("Access-Control-Allow-Methods: GET, POST, OPTIONS");         

    if (isset($_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']))
        header("Access-Control-Allow-Headers: {$_SERVER['HTTP_ACCESS_CONTROL_REQUEST_HEADERS']}, X-API-KEY, Content-Type, Cache-Control");

    exit(0);
}

// At the start of the file, after CORS headers
if (!isset($_SERVER['HTTP_X_API_KEY'])) {
    http_response_code(401);
    echo json_encode(['error' => 'No API key provided']);
    exit();
}

$apiKey = $_SERVER['HTTP_X_API_KEY'];

if (!isValidApiKey($apiKey)) {
    error_log("Invalid API Key received: " . substr($apiKey, 0, 10) . "...");
    http_response_code(403);
    echo json_encode([
        'error' => 'Forbidden - Invalid API Key',
        'debug' => [
            'received_key_prefix' => substr($apiKey, 0, 10),
            'headers' => getallheaders()
        ]
    ]);
    exit();
}

// Database connection settings
define('DB_HOST', 'localhost');
define('DB_USER', 'uug5g5w5itxu3');
define('DB_PASS', '$1@^Kig=ct16');
define('DB_NAME', 'dbun4qlgn4ggyo');

// Connect to the database
function dbConnect() {
    $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
    if ($conn->connect_error) {
        die("Connection failed: " . $conn->connect_error);
    }
    return $conn;
}

// Search articles by a comma-separated list of keywords
function searchArticles($keywords = null, $startDate = null, $endDate = null, $page = 1) {
    $conn = dbConnect();
    $articlesPerPage = 6;
    $offset = ($page - 1) * $articlesPerPage;

    // Initialize WHERE clause fragments
    $whereClauses = [];

    if ($keywords) {
        $keywordsArray = array_map('trim', explode(',', $keywords));
        foreach ($keywordsArray as $keyword) {
            $sanitizedKeyword = $conn->real_escape_string($keyword);
            $keywordWhereClause = "(topic LIKE '%$sanitizedKeyword%' OR AIHeadline LIKE '%$sanitizedKeyword%' OR AIStory LIKE '%$sanitizedKeyword%')";
            $whereClauses[] = $keywordWhereClause;
        }
    }

    if ($startDate && $endDate) {
        $sanitizedStartDate = $conn->real_escape_string($startDate);
        $sanitizedEndDate = $conn->real_escape_string($endDate);
        $whereClauses[] = "(Published BETWEEN '$sanitizedStartDate' AND '$sanitizedEndDate')";
    } elseif ($startDate) {
        $sanitizedStartDate = $conn->real_escape_string($startDate);
        $whereClauses[] = "(Published >= '$sanitizedStartDate')";
    } elseif ($endDate) {
        $sanitizedEndDate = $conn->real_escape_string($endDate);
        $whereClauses[] = "(Published <= '$sanitizedEndDate')";
    }

    // Combine all conditions
    $combinedWhereClause = implode(' AND ', $whereClauses);

    // If there are no conditions, set a default
    if (empty($combinedWhereClause)) {
        $combinedWhereClause = "1"; // '1' means always true, fetches all records
    }

    // Get total count for pagination
    $countQuery = "SELECT COUNT(*) as total FROM articles WHERE $combinedWhereClause";
    $countResult = $conn->query($countQuery);
    $totalArticles = $countResult->fetch_assoc()['total'];
    $totalPages = ceil($totalArticles / $articlesPerPage);

    // Get paginated results
    $query = "SELECT ID, AIHeadline, AIStory, AIHaiku, Published, CONCAT('https://ainewsbrew.com/article/', ID) as link, bs, Cited, image_data, image_haiku, bs_p, AISummary, QAS, review_status
              FROM articles 
              WHERE $combinedWhereClause
              ORDER BY Published DESC
              LIMIT $offset, $articlesPerPage";

    $result = $conn->query($query);
    $articles = [];
    if ($result && $result->num_rows > 0) {
        while($row = $result->fetch_assoc()) {
            array_push($articles, $row);
        }
    }
    $conn->close();

    // Return both the articles and pagination info
    return json_encode([
        'articles' => $articles,
        'pagination' => [
            'currentPage' => (int)$page,
            'totalPages' => $totalPages,
            'totalArticles' => $totalArticles,
            'articlesPerPage' => $articlesPerPage
        ]
    ]);
}

// Search articles by a comma-separated list of keywords
function detailArticles($articleIds) {
    $conn = dbConnect();

    // Sanitize and prepare the IDs for SQL query
    $sanitizedIds = array_map(function($id) use ($conn) {
        return $conn->real_escape_string($id);
    }, $articleIds);
    $idsString = implode(',', $sanitizedIds);

    $query = "SELECT ID, AIHeadline, AIStory, AIHaiku, Published, CONCAT('https://ainewsbrew.com/article/', ID) as link, bs, Cited, image_data, image_haiku, bs_p, AISummary, QAS, review_status
    FROM articles 
    WHERE ID IN ($idsString)";

    $result = $conn->query($query);

    $articles = [];
    if ($result && $result->num_rows > 0) {
        while($row = $result->fetch_assoc()) {
            array_push($articles, $row);
        }
    }
    $conn->close();
    return json_encode($articles);
}

// Publish an article
function publishArticle($articleData) {
    $conn = dbConnect();
    // Extract and sanitize input data
    $AIHeadline = $conn->real_escape_string($articleData['AIHeadline']);
    $AISummary = $conn->real_escape_string($articleData['AISummary']);
    $AIStory = $conn->real_escape_string($articleData['AIStory']);
    $AIHaiku = $conn->real_escape_string($articleData['AIHaiku']);
    $deta_bs_align = $conn->real_escape_string($articleData['deta_bs_align']);
    $bs = $conn->real_escape_string($articleData['bs']);
    $bs_p = $conn->real_escape_string($articleData['bs_p']);
    $Cited = $conn->real_escape_string($articleData['Cited']);
    $topic = $conn->real_escape_string($articleData['topic']);
    $cat = $conn->real_escape_string($articleData['cat']);
    $qas = $conn->real_escape_string($articleData['qas']);
    $image_data = isset($articleData['image_data']) ? $conn->real_escape_string($articleData['image_data']) : null;
    $image_haiku = isset($articleData['image_haiku']) ? $conn->real_escape_string($articleData['image_haiku']) : null;

    $query = "INSERT INTO articles (AIHeadline, AISummary, AIStory, AIHaiku, deta_bs_align, bs, bs_p, Cited, topic, Published, cat, QAS, image_data, image_haiku) 
              VALUES (
                  '$AIHeadline', 
                  '$AISummary', 
                  '$AIStory', 
                  '$AIHaiku', 
                  '$deta_bs_align', 
                  '$bs', 
                  '$bs_p', 
                  '$Cited', 
                  '$topic', 
                  CURRENT_TIMESTAMP, 
                  '$cat',
                  '$qas',
                  " . ($image_data ? "'$image_data'" : "NULL") . ",
                  " . ($image_haiku ? "'$image_haiku'" : "NULL") . "
              )";
    
    if ($conn->query($query) === TRUE) {
        $newArticleId = $conn->insert_id;
        $articleLink = "https://ainewsbrew.com/article/" . $newArticleId;
        $response = [
            "status" => "success", 
            "message" => "Article published successfully", 
            "articleId" => $newArticleId, 
            "link" => $articleLink
        ];
    } else {
        $response = ["status" => "error", "message" => "Error: " . $conn->error];
    }
    $conn->close();
    return json_encode($response);
}

// Function to get the stored API key
function getStoredApiKey() {
    // Replace with the actual method to retrieve your stored API key
    // For example, it can be fetched from an environment variable
    return '6f8c18d140739e52d1e13522629a7f1d1625040844ccb86f2d625998dfaaf7b9';
}

// Function to check the API key from the request
function isValidApiKey($apiKey) {
    $storedApiKey = getStoredApiKey();
    // Add debug logging
    error_log("Received API Key: " . substr($apiKey, 0, 10) . "...");
    error_log("Stored API Key: " . substr($storedApiKey, 0, 10) . "...");
    return $apiKey === $storedApiKey;
}

// Function to handle publication
function handleSearch() {
    // Retrieve parameters from the query parameters
    $keywords = $_GET['keywords'] ?? '';
    $startDate = $_GET['startDate'] ?? null;
    $endDate = $_GET['endDate'] ?? null;
    $page = isset($_GET['page']) ? max(1, (int)$_GET['page']) : 1; // Ensure page is at least 1

    // Call the searchArticles function with all parameters
    $searchResults = searchArticles($keywords, $startDate, $endDate, $page);

    // Send the search results as JSON
    header('Content-Type: application/json');
    echo $searchResults;
}

function handleDetailedSearch() {
    // Decode the JSON body from the request
    $data = json_decode(file_get_contents('php://input'), true);

    // Check if 'articleIds' is provided in the request
    if (!isset($data['articleIds']) || !is_array($data['articleIds'])) {
        header('Content-Type: application/json');
        echo json_encode(['error' => 'Article IDs required']);
        return;
    }

    $articleIds = $data['articleIds'];

    // Call the getArticleDetails function
    $detailedResults = detailArticles($articleIds);

    // Send the detailed search results as JSON
    header('Content-Type: application/json');
    echo $detailedResults;
}

function getLatestArticles() {
    $conn = dbConnect();
    $query = "SELECT ID, AIHeadline, AIHaiku, Published,bs_p,qas,CONCAT('https://ainewsbrew.com/article/', ID) as link,topic,cat
              FROM articles 
              ORDER BY Published DESC
              ";
    $result = $conn->query($query);
    $articles = [];
    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $articles[] = $row;
        }
    }
    $conn->close();
    return json_encode($articles);
}

function getArticleByIndex($index) {
    $conn = dbConnect();
    $index = intval($index); // Ensure the index is an integer
    $query = "SELECT ID, AIHeadline, AIStory, AIHaiku, Published, CONCAT('https://ainewsbrew.com/article/', ID) as link, image_data, image_haiku, Cited, topic, cat, bs, bs_p, AISummary, QAS, review_status
              FROM articles 
              ORDER BY Published DESC
              LIMIT $index, 1";
    $result = $conn->query($query);
    $article = null;
    if ($result && $result->num_rows > 0) {
        $article = $result->fetch_assoc();
    }
    $conn->close();
    return json_encode($article);
}

function getNextMissingHaikuImage() {
    $conn = dbConnect();
    $query = "SELECT ID, AIHeadline, AIStory, AIHaiku, Published, image_data, image_haiku, topic, cat
              FROM articles 
              WHERE image_haiku IS NULL OR image_haiku = ''
              ORDER BY Published DESC
              LIMIT 1";
    
    $result = $conn->query($query);
    $article = null;
    if ($result && $result->num_rows > 0) {
        $article = $result->fetch_assoc();
    }
    $conn->close();
    return json_encode($article);
}

function updateArticleImages($articleId, $imageData) {
    $conn = dbConnect();
    
    // Sanitize inputs
    $articleId = $conn->real_escape_string($articleId);
    $image_data = isset($imageData['image_data']) ? $conn->real_escape_string($imageData['image_data']) : null;
    $image_haiku = isset($imageData['image_haiku']) ? $conn->real_escape_string($imageData['image_haiku']) : null;
    
    $query = "UPDATE articles 
              SET image_data = " . ($image_data ? "'$image_data'" : "NULL") . ",
                  image_haiku = " . ($image_haiku ? "'$image_haiku'" : "NULL") . "
              WHERE ID = '$articleId'";
    
    if ($conn->query($query) === TRUE) {
        $response = ["status" => "success", "message" => "Images updated successfully"];
    } else {
        $response = ["status" => "error", "message" => "Error: " . $conn->error];
    }
    
    $conn->close();
    return json_encode($response);
}

function getDashboardMetrics() {
    $conn = dbConnect();
    $metrics = [];

    // Get total number of articles
    $totalQuery = "SELECT COUNT(*) as total FROM articles";
    $result = $conn->query($totalQuery);
    $metrics['totalArticles'] = $result->fetch_assoc()['total'];

    // Get count of approved articles
    $approvedQuery = "SELECT COUNT(*) as approved_total 
                      FROM articles 
                      WHERE review_status = 'approved'";
    $result = $conn->query($approvedQuery);
    $metrics['approvedArticles'] = $result->fetch_assoc()['approved_total'];

    // Get count of rejected articles
    $rejectedQuery = "SELECT COUNT(*) as rejected_total 
                      FROM articles 
                      WHERE review_status = 'rejected'";
    $result = $conn->query($rejectedQuery);
    $metrics['rejectedArticles'] = $result->fetch_assoc()['rejected_total'];

    // Get average QAS score
    $qasQuery = "SELECT AVG(CAST(QAS AS DECIMAL(10,2))) as avg_qas 
                 FROM articles 
                 WHERE QAS IS NOT NULL 
                 AND QAS != ''
                 AND QAS REGEXP '^[0-9.-]+$'";
    $result = $conn->query($qasQuery);
    $metrics['averageQualityScore'] = round($result->fetch_assoc()['avg_qas'], 2);

    // Get average publications per day
    $avgQuery = "SELECT AVG(articles_per_day) as avg_per_day 
                 FROM (
                     SELECT DATE(Published) as pub_date, COUNT(*) as articles_per_day 
                     FROM articles 
                     GROUP BY DATE(Published)
                 ) daily_counts";
    $result = $conn->query($avgQuery);
    $metrics['averageArticlesPerDay'] = round($result->fetch_assoc()['avg_per_day'], 2);

    // Get average bs_p score
    $bsQuery = "SELECT AVG(CAST(bs_p AS DECIMAL(10,2))) as avg_bs_p 
                FROM articles 
                WHERE bs_p IS NOT NULL 
                AND bs_p != ''
                AND bs_p REGEXP '^[0-9.-]+$'";
    $result = $conn->query($bsQuery);
    $metrics['averageBiasScore'] = round($result->fetch_assoc()['avg_bs_p'], 2);

    // Get category distribution
    $catQuery = "SELECT cat, COUNT(*) as count 
                 FROM articles 
                 WHERE cat IS NOT NULL AND cat != '' 
                 GROUP BY cat 
                 ORDER BY count DESC";
    $result = $conn->query($catQuery);
    $categories = [];
    while ($row = $result->fetch_assoc()) {
        $categories[] = $row;
    }
    $metrics['categoryDistribution'] = $categories;

    // Get word cloud data from topics
    $wordCloudQuery = "
        WITH RECURSIVE
        numbers AS (
            SELECT 1 as n UNION ALL SELECT n + 1 FROM numbers WHERE n < 100
        ),
        split_words AS (
            SELECT 
                LOWER(
                    TRIM(
                        SUBSTRING_INDEX(
                            SUBSTRING_INDEX(
                                REPLACE(
                                    REPLACE(topic, ',', ' '),
                                    '  ', ' '
                                ),
                                ' ',
                                n
                            ),
                            ' ',
                            -1
                        )
                    )
                ) as word
            FROM articles
            CROSS JOIN numbers n
            WHERE 
                n <= 1 + (
                    LENGTH(topic) - 
                    LENGTH(REPLACE(REPLACE(topic, ',', ' '), ' ', '')) + 1
                )
                AND Published >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        )
        SELECT 
            word as text,
            COUNT(*) as value
        FROM split_words
        WHERE 
            LENGTH(word) > 2
            AND word NOT IN (
                'the', 'and', 'for', 'that', 'this', 'but', 'with', 'from',
                'has', 'was', 'are', 'have', 'had', 'not', 'its', 'it\'s',
                'they', 'their', 'what', 'about', 'which', 'when', 'would',
                'there', 'been', 'could', 'into', 'than', 'who', 'will'
            )
        GROUP BY word
        HAVING COUNT(*) > 1
        ORDER BY value DESC
        LIMIT 100";

    $result = $conn->query($wordCloudQuery);
    $wordCloud = [];
    while ($row = $result->fetch_assoc()) {
        $wordCloud[] = [
            'text' => $row['text'],
            'value' => (int)$row['value']
        ];
    }
    $metrics['wordCloudData'] = $wordCloud;

    // Get source rankings
    $sourceQuery = "
        WITH RECURSIVE
        numbers AS (
            SELECT 1 as n UNION ALL SELECT n + 1 FROM numbers WHERE n < 100
        ),
        parsed_urls AS (
            SELECT 
                ID,
                SUBSTRING_INDEX(
                    SUBSTRING_INDEX(
                        SUBSTRING_INDEX(
                            SUBSTRING_INDEX(
                                JSON_UNQUOTE(
                                    JSON_EXTRACT(
                                        JSON_EXTRACT(Cited, '$[*][0]'),
                                        '$[0]'
                                    )
                                ),
                                '/', 3
                            ),
                            '//', -1
                        ),
                        'www.', -1
                    ),
                    '/', 1
                ) as domain
            FROM articles
            WHERE Cited IS NOT NULL AND Cited != '[]' AND Cited != ''
        )
        SELECT 
            domain,
            COUNT(*) as article_count,
            COUNT(*) * 100.0 / (SELECT COUNT(*) FROM parsed_urls) as percentage
        FROM parsed_urls
        GROUP BY domain
        ORDER BY article_count DESC
        LIMIT 10";

    $result = $conn->query($sourceQuery);
    $sourceRankings = [];
    while ($row = $result->fetch_assoc()) {
        $sourceRankings[] = [
            'domain' => $row['domain'],
            'count' => (int)$row['article_count'],
            'percentage' => round((float)$row['percentage'], 2)
        ];
    }
    $metrics['sourceRankings'] = $sourceRankings;

    $conn->close();
    return json_encode($metrics);
}

function getNextUnreviewedArticle() {
    $conn = dbConnect();
    $query = "SELECT ID, AIHeadline, AIStory, AIHaiku, cat, topic, bs, bs_p, Cited
              FROM articles 
              WHERE review_status IS NULL
              ORDER BY Published DESC
              LIMIT 1";
    
    $result = $conn->query($query);
    $article = null;
    if ($result && $result->num_rows > 0) {
        $article = $result->fetch_assoc();
    }
    $conn->close();
    return json_encode($article);
}

function updateArticleReviewStatus($articleId, $status, $updates = []) {
    $conn = dbConnect();
    
    // Sanitize inputs
    $articleId = $conn->real_escape_string($articleId);
    $status = $conn->real_escape_string($status);
    
    // Build the UPDATE query dynamically
    $updateFields = ["review_status = '$status'", "reviewed_at = CURRENT_TIMESTAMP"];
    
    // Add optional update fields if they exist
    if (isset($updates['cat'])) {
        $cat = $conn->real_escape_string($updates['cat']);
        $updateFields[] = "cat = '$cat'";
    }
    if (isset($updates['topic'])) {
        $topic = $conn->real_escape_string($updates['topic']);
        $updateFields[] = "topic = '$topic'";
    }
    if (isset($updates['bs_p'])) {
        $bs_p = $conn->real_escape_string($updates['bs_p']);
        $updateFields[] = "bs_p = '$bs_p'";
    }
    if (isset($updates['qas'])) {
        $qas = $conn->real_escape_string($updates['qas']);
        $updateFields[] = "QAS = '$qas'";
    }
    // Add AISummary update
    if (isset($updates['reasoning'])) {
        $reasoning = $conn->real_escape_string($updates['reasoning']);
        $updateFields[] = "AISummary = '$reasoning'";
    }
    
    $updateString = implode(", ", $updateFields);
    $query = "UPDATE articles 
              SET $updateString
              WHERE ID = '$articleId'";
    
    if ($conn->query($query) === TRUE) {
        $response = ["status" => "success", "message" => "Article updated successfully"];
    } else {
        $response = ["status" => "error", "message" => "Error: " . $conn->error];
    }
    
    $conn->close();
    return json_encode($response);
}

function getWordCloudData($startDate = null, $endDate = null) {
    $conn = dbConnect();
    
    // Build date range condition
    $dateCondition = "1=1"; // Default to all dates if none specified
    if ($startDate && $endDate) {
        $startDate = $conn->real_escape_string($startDate);
        $endDate = $conn->real_escape_string($endDate);
        $dateCondition = "Published BETWEEN '$startDate' AND '$endDate'";
    } elseif ($startDate) {
        $startDate = $conn->real_escape_string($startDate);
        $dateCondition = "Published >= '$startDate'";
    } elseif ($endDate) {
        $endDate = $conn->real_escape_string($endDate);
        $dateCondition = "Published <= '$endDate'";
    }

    $wordCloudQuery = "
        WITH RECURSIVE
        numbers AS (
            SELECT 1 as n UNION ALL SELECT n + 1 FROM numbers WHERE n < 100
        ),
        split_words AS (
            SELECT 
                LOWER(
                    TRIM(
                        SUBSTRING_INDEX(
                            SUBSTRING_INDEX(
                                REPLACE(
                                    REPLACE(topic, ',', ' '),
                                    '  ', ' '
                                ),
                                ' ',
                                n
                            ),
                            ' ',
                            -1
                        )
                    )
                ) as word
            FROM articles
            CROSS JOIN numbers n
            WHERE 
                n <= 1 + (
                    LENGTH(topic) - 
                    LENGTH(REPLACE(REPLACE(topic, ',', ' '), ' ', '')) + 1
                )
                AND $dateCondition
        )
        SELECT 
            word as text,
            COUNT(*) as value
        FROM split_words
        WHERE 
            LENGTH(word) > 2
            AND word NOT IN (
                'the', 'and', 'for', 'that', 'this', 'but', 'with', 'from',
                'has', 'was', 'are', 'have', 'had', 'not', 'its', 'it\'s',
                'they', 'their', 'what', 'about', 'which', 'when', 'would',
                'there', 'been', 'could', 'into', 'than', 'who', 'will'
            )
        GROUP BY word
        HAVING COUNT(*) > 1
        ORDER BY value DESC
        LIMIT 100";

    $result = $conn->query($wordCloudQuery);
    $wordCloud = [];
    while ($row = $result->fetch_assoc()) {
        $wordCloud[] = [
            'text' => $row['text'],
            'value' => (int)$row['value']
        ];
    }
    
    $conn->close();
    return json_encode([
        'status' => 'success',
        'data' => $wordCloud,
        'dateRange' => [
            'start' => $startDate ?? 'all',
            'end' => $endDate ?? 'all'
        ]
    ]);
}

// New endpoint for historical research
function searchHistoricalArticles($keywords, $timeRange, $filters = []) {
    try {
        $conn = dbConnect();
        if (!$conn) {
            throw new Exception("Database connection failed");
        }
        
        $articlesPerPage = 200;
        $page = $filters['page'] ?? 1;
        $offset = ($page - 1) * $articlesPerPage;

        // Initialize WHERE clauses and debug info
        $whereClauses = [];
        $debugInfo = [
            'input' => [
                'keywords' => $keywords,
                'timeRange' => $timeRange,
                'filters' => $filters
            ],
            'processedClauses' => [],
            'errors' => []
        ];
        
        // Keyword processing in searchHistoricalArticles function
        if ($keywords) {
            $keywordClauses = [];
            // Split by comma first
            $keywordGroups = array_map('trim', explode(',', $keywords));
            
            $debugInfo['processedClauses']['keywords'] = [];
            
            foreach ($keywordGroups as $keywordGroup) {
                $groupClauses = [];
                
                // Check if this is an OR group (contains |)
                if (strpos($keywordGroup, '|') !== false) {
                    $orTerms = array_map('trim', explode('|', $keywordGroup));
                    $orClauses = [];
                    foreach ($orTerms as $term) {
                        $sanitizedTerm = $conn->real_escape_string($term);
                        $clause = "(topic REGEXP '(^|[[:space:],.])" . $sanitizedTerm . "([[:space:],.]|$)' OR " .
                                 "AIHeadline REGEXP '(^|[[:space:],.])" . $sanitizedTerm . "([[:space:],.]|$)' OR " .
                                 "AIStory REGEXP '(^|[[:space:],.])" . $sanitizedTerm . "([[:space:],.]|$)')";
                        $orClauses[] = $clause;
                        $debugInfo['processedClauses']['keywords'][] = [
                            'type' => 'or_term',
                            'original' => $term,
                            'sanitized' => $sanitizedTerm,
                            'clause' => $clause
                        ];
                    }
                    $groupClauses[] = "(" . implode(" OR ", $orClauses) . ")";
                }
                // Handle quoted phrases
                elseif (preg_match('/^"(.*)"$/', $keywordGroup, $matches)) {
                    $exactPhrase = $conn->real_escape_string($matches[1]);
                    $clause = "(topic REGEXP '(^|[[:space:],.])" . $exactPhrase . "([[:space:],.]|$)' OR " .
                             "AIHeadline REGEXP '(^|[[:space:],.])" . $exactPhrase . "([[:space:],.]|$)' OR " .
                             "AIStory REGEXP '(^|[[:space:],.])" . $exactPhrase . "([[:space:],.]|$)')";
                    $groupClauses[] = $clause;
                    $debugInfo['processedClauses']['keywords'][] = [
                        'type' => 'exact_phrase',
                        'original' => $keywordGroup,
                        'processed' => $exactPhrase,
                        'clause' => $clause
                    ];
                }
                // Handle AND operator
                elseif (strpos($keywordGroup, ' AND ') !== false) {
                    $andTerms = array_map('trim', explode(' AND ', $keywordGroup));
                    $andClauses = [];
                    foreach ($andTerms as $term) {
                        $sanitizedTerm = $conn->real_escape_string($term);
                        $clause = "(topic REGEXP '(^|[[:space:],.])" . $sanitizedTerm . "([[:space:],.]|$)' OR " .
                                 "AIHeadline REGEXP '(^|[[:space:],.])" . $sanitizedTerm . "([[:space:],.]|$)' OR " .
                                 "AIStory REGEXP '(^|[[:space:],.])" . $sanitizedTerm . "([[:space:],.]|$)')";
                        $andClauses[] = $clause;
                        $debugInfo['processedClauses']['keywords'][] = [
                            'type' => 'and_term',
                            'original' => $term,
                            'sanitized' => $sanitizedTerm,
                            'clause' => $clause
                        ];
                    }
                    $groupClauses[] = "(" . implode(" AND ", $andClauses) . ")";
                }
                // Simple keyword
                else {
                    $sanitizedKeyword = $conn->real_escape_string($keywordGroup);
                    $clause = "(topic REGEXP '(^|[[:space:],.])" . $sanitizedKeyword . "([[:space:],.]|$)' OR " .
                             "AIHeadline REGEXP '(^|[[:space:],.])" . $sanitizedKeyword . "([[:space:],.]|$)' OR " .
                             "AIStory REGEXP '(^|[[:space:],.])" . $sanitizedKeyword . "([[:space:],.]|$)')";
                    $groupClauses[] = $clause;
                    $debugInfo['processedClauses']['keywords'][] = [
                        'type' => 'simple',
                        'original' => $keywordGroup,
                        'sanitized' => $sanitizedKeyword,
                        'clause' => $clause
                    ];
                }
                
                // Add the processed group clauses
                if (!empty($groupClauses)) {
                    $keywordClauses[] = implode(" AND ", $groupClauses);
                }
            }
            
            // Combine all keyword groups with AND by default
            $combinedKeywordClause = "(" . implode(" AND ", $keywordClauses) . ")";
            $whereClauses[] = $combinedKeywordClause;
            $debugInfo['processedClauses']['final_keyword_clause'] = $combinedKeywordClause;
        }

        // Handle additional filters
        $debugInfo['processedClauses']['filters'] = [];
        
        if (!empty($filters['category'])) {
            $category = $conn->real_escape_string($filters['category']);
            $clause = "cat = '$category'";
            $whereClauses[] = $clause;
            $debugInfo['processedClauses']['filters']['category'] = [
                'original' => $filters['category'],
                'sanitized' => $category,
                'clause' => $clause
            ];
        }

        if (!empty($filters['biasRange'])) {
            $minBias = floatval($filters['biasRange'][0]);
            $maxBias = floatval($filters['biasRange'][1]);
            $clause = "CAST(bs_p AS DECIMAL(10,2)) BETWEEN $minBias AND $maxBias";
            $whereClauses[] = $clause;
            $debugInfo['processedClauses']['filters']['biasRange'] = [
                'original' => $filters['biasRange'],
                'processed' => [$minBias, $maxBias],
                'clause' => $clause
            ];
        }

        if (!empty($filters['qualityRange'])) {
            $minQuality = floatval($filters['qualityRange'][0]);
            $maxQuality = floatval($filters['qualityRange'][1]);
            $clause = "CAST(QAS AS DECIMAL(10,2)) BETWEEN $minQuality AND $maxQuality";
            $whereClauses[] = $clause;
            $debugInfo['processedClauses']['filters']['qualityRange'] = [
                'original' => $filters['qualityRange'],
                'processed' => [$minQuality, $maxQuality],
                'clause' => $clause
            ];
        }

        // Time range processing
        $timeRangeMap = [
            '90d' => '90 DAY',
            '180d' => '180 DAY',
            '365d' => '365 DAY',
            '730d' => '730 DAY',
            '1825d' => '1825 DAY',
            'all' => null  // Handle 'all' specially
        ];

        $debugInfo['processedClauses']['timeRange'] = [
            'original' => $timeRange,
            'mapped' => $timeRangeMap[$timeRange] ?? null
        ];

        if ($timeRange && $timeRange !== 'all') {
            if (isset($timeRangeMap[$timeRange])) {
                $interval = $timeRangeMap[$timeRange];
                $clause = "Published >= DATE_SUB(NOW(), INTERVAL $interval)";
                $whereClauses[] = $clause;
                $debugInfo['processedClauses']['timeRange']['clause'] = $clause;
            }
        }

        // Combine all conditions
        $whereClause = !empty($whereClauses) ? "WHERE " . implode(" AND ", $whereClauses) : "";
        $debugInfo['final_where_clause'] = $whereClause;

        // Get total count for pagination
        $countQuery = "SELECT COUNT(*) as total FROM articles $whereClause";
        $debugInfo['queries']['count'] = $countQuery;
        
        $countResult = $conn->query($countQuery);
        $totalArticles = $countResult->fetch_assoc()['total'];
        $totalPages = ceil($totalArticles / $articlesPerPage);

        // Main query with pagination
        $query = "SELECT 
                    ID,
                    AIHeadline,
                    AIStory,
                    AIHaiku,
                    Published,
                    cat as category,
                    bs_p as biasScore,
                    QAS as qualityScore,
                    topic,
                    CONCAT('https://ainewsbrew.com/article/', ID) as link
                  FROM articles 
                  $whereClause
                  ORDER BY Published DESC
                  LIMIT $offset, $articlesPerPage";
                  
        $debugInfo['queries']['main'] = $query;

        $result = $conn->query($query);
        $articles = [];
        
        if ($result && $result->num_rows > 0) {
            while($row = $result->fetch_assoc()) {
                // Convert numeric strings to proper types
                $row['biasScore'] = is_numeric($row['biasScore']) ? floatval($row['biasScore']) : null;
                $row['qualityScore'] = is_numeric($row['qualityScore']) ? floatval($row['qualityScore']) : null;
                $articles[] = $row;
            }
        }

        $conn->close();

        return [
            'status' => 'success',
            'articles' => $articles,
            'metadata' => [
                'totalResults' => $totalArticles,
                'pageSize' => $articlesPerPage,
                'currentPage' => $page,
                'totalPages' => $totalPages
            ],
            'debug' => $debugInfo
        ];
        
    } catch (Exception $e) {
        if (isset($conn)) {
            $conn->close();
        }
        error_log("searchHistoricalArticles Error: " . $e->getMessage());
        throw $e;
    }
}

// Main logic
$mode = $_GET['mode'] ?? '';

switch ($mode) {
    case 'searchSummary':
        handleSearch();
        break;
    case 'detailSearch':
        handleDetailedSearch();
        break;
    case 'pub':
        $articleData = json_decode(file_get_contents('php://input'), true);
        echo publishArticle($articleData);
        break;
    case 'latest':
        echo getLatestArticles();
        break;
    case 'byIndex':
        $index = $_GET['index'] ?? 0;
        echo getArticleByIndex($index);
        break;
    case 'getMissingHaiku':
        echo getNextMissingHaikuImage();
        break;
    case 'updateImages':
        $articleId = $_GET['id'] ?? null;
        $imageData = json_decode(file_get_contents('php://input'), true);
        if ($articleId) {
            echo updateArticleImages($articleId, $imageData);
        } else {
            echo json_encode(['error' => 'Article ID required']);
        }
        break;
    case 'dashboard':
        echo getDashboardMetrics();
        break;
    case 'getUnreviewed':
        echo getNextUnreviewedArticle();
        break;
    case 'updateReviewStatus':
        $articleId = $_GET['id'] ?? null;
        $status = $_GET['status'] ?? null;
        $updates = json_decode(file_get_contents('php://input'), true) ?? [];
        
        if ($articleId && $status) {
            echo updateArticleReviewStatus($articleId, $status, $updates);
        } else {
            echo json_encode(['error' => 'Article ID and status required']);
        }
        break;
    case 'wordcloud':
        $startDate = $_GET['startDate'] ?? null;
        $endDate = $_GET['endDate'] ?? null;
        echo getWordCloudData($startDate, $endDate);
        break;
    case 'historical':
        try {
            $keywords = $_GET['keywords'] ?? '';
            $timeRange = $_GET['timeRange'] ?? '24h';
            $filters = json_decode(file_get_contents('php://input'), true) ?? [];
            
            // Debug logging
            error_log("Historical Search Request - Keywords: " . $keywords);
            error_log("Historical Search Request - TimeRange: " . $timeRange);
            error_log("Historical Search Request - Filters: " . json_encode($filters));
            
            // Validate input
            if (empty($keywords)) {
                $error = ['error' => 'Keywords required', 'request' => [
                    'keywords' => $keywords,
                    'timeRange' => $timeRange,
                    'filters' => $filters
                ]];
                error_log("Historical Search Error: Keywords missing");
                echo json_encode($error);
                break;
            }
            
            try {
                $results = searchHistoricalArticles($keywords, $timeRange, $filters);
                header('Content-Type: application/json');
                
                if (empty($results['articles'])) {
                    error_log("Historical Search: No results found for keywords: " . $keywords);
                }
                
                echo json_encode($results);
            } catch (Exception $e) {
                error_log("Historical Search Error in searchHistoricalArticles: " . $e->getMessage());
                echo json_encode([
                    'error' => 'Search failed',
                    'message' => $e->getMessage(),
                    'request' => [
                        'keywords' => $keywords,
                        'timeRange' => $timeRange,
                        'filters' => $filters
                    ],
                    'trace' => $e->getTraceAsString()
                ]);
            }
        } catch (Exception $e) {
            error_log("Historical Search Outer Error: " . $e->getMessage());
            echo json_encode([
                'error' => 'Request processing failed',
                'message' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
        }
        break;
    default:
        header('Content-Type: application/json');
        echo json_encode(['error' => 'Invalid mode']);
}
?>