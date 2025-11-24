<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo isset($pageTitle) ? $pageTitle . ' - ' : ''; ?>KBO 야구 일정 관리</title>
    <link rel="stylesheet" href="style.css?v=<?php echo time(); ?>">
</head>
<body>
    <header>
        <nav class="navbar">
            <div class="container">
                <h1 class="logo"><a href="index.php">KBO 야구 일정</a></h1>
                <ul class="nav-menu">
                    <li><a href="index.php">홈</a></li>
                    <li><a href="matches.php">경기 일정</a></li>
                    <li><a href="teams.php">팀 목록</a></li>
                    <li><a href="stadiums.php">경기장 정보</a></li>
                    <li><a href="statistics.php">통계 분석</a></li>
                </ul>
            </div>
        </nav>
    </header>
    <main class="container">


